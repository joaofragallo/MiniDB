"""Índice B+ persistente: chaves uint32 únicas apontam para RIDs do MiniDB."""

import os
import struct
from bisect import bisect_left, bisect_right

from minidb import Cache, QUANTIDADE_SLOTS, TAMANHO_PAGINA, le_pagina, escreve_pagina


METADADOS = struct.Struct("<8sIII")  # assinatura, total, raiz, capacidade
CABECALHO_NO = struct.Struct("<B3xII4x")  # folha, quantidade, próxima folha
ENTRADA = struct.Struct("<III")  # chave, página do registro, slot
MAXIMO_CHAVES = (TAMANHO_PAGINA - CABECALHO_NO.size) // ENTRADA.size


class _ArquivoIndice:
    """Fornece páginas de índice ao mesmo Cache usado pelo M2."""

    def __init__(self, caminho, capacidade):
        self.caminho = caminho
        self.leituras = 0
        if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
            self.quantidade_paginas = 1
            self.raiz = 0
            self.capacidade = MAXIMO_CHAVES if capacidade is None else capacidade
            self.salva_metadados()
        else:
            assinatura, total, raiz, limite = METADADOS.unpack_from(le_pagina(caminho, 0))
            if (assinatura != b"MDBIDX01" or
                    os.path.getsize(caminho) != total * TAMANHO_PAGINA or
                    not 1 <= raiz < total or not 3 <= limite <= MAXIMO_CHAVES):
                raise ValueError("Arquivo de índice inválido")
            if capacidade is not None and capacidade != limite:
                raise ValueError("Capacidade diferente da gravada no índice")
            self.quantidade_paginas, self.raiz, self.capacidade = total, raiz, limite

    def salva_metadados(self):
        dados = bytearray(TAMANHO_PAGINA)
        METADADOS.pack_into(dados, 0, b"MDBIDX01", self.quantidade_paginas,
                            self.raiz, self.capacidade)
        escreve_pagina(self.caminho, 0, dados)

    def _valida_pagina(self, numero):
        if not 1 <= numero < self.quantidade_paginas:
            raise ValueError("Página de índice não alocada")

    def aloca(self):
        numero = self.quantidade_paginas
        escreve_pagina(self.caminho, numero, bytearray(TAMANHO_PAGINA))
        self.quantidade_paginas += 1
        return numero

    def le_pagina(self, numero):
        self._valida_pagina(numero)
        self.leituras += 1
        return le_pagina(self.caminho, numero)

    def escreve_pagina(self, numero, dados):
        self._valida_pagina(numero)
        escreve_pagina(self.caminho, numero, dados)

    def sync(self):
        self.salva_metadados()
        with open(self.caminho, "r+b") as arquivo:
            os.fsync(arquivo.fileno())


class _No:
    def __init__(self, folha=True, chaves=None, valores=None, proxima=0):
        self.folha = folha
        self.chaves = [] if chaves is None else chaves
        # RIDs nas folhas; números de páginas dos filhos nos internos.
        self.valores = [] if valores is None else valores
        self.proxima = proxima

    @classmethod
    def de_bytes(cls, dados):
        folha, quantidade, proxima = CABECALHO_NO.unpack_from(dados)
        inicio = CABECALHO_NO.size
        if folha:
            fim = inicio + quantidade * ENTRADA.size
            entradas = list(ENTRADA.iter_unpack(dados[inicio:fim]))
            chaves = [chave for chave, pagina, slot in entradas]
            rids = [(pagina, slot) for chave, pagina, slot in entradas]
            return cls(True, chaves, rids, proxima)
        numeros = struct.unpack_from(f"<{2 * quantidade + 1}I", dados, inicio)
        return cls(False, list(numeros[:quantidade]), list(numeros[quantidade:]))

    def como_bytes(self):
        dados = bytearray(TAMANHO_PAGINA)
        CABECALHO_NO.pack_into(dados, 0, self.folha, len(self.chaves), self.proxima)
        inicio = CABECALHO_NO.size
        if self.folha:
            for chave, rid in zip(self.chaves, self.valores):
                ENTRADA.pack_into(dados, inicio, chave, *rid)
                inicio += ENTRADA.size
        else:
            numeros = self.chaves + self.valores
            struct.pack_into(f"<{len(numeros)}I", dados, inicio, *numeros)
        return dados


class ArvoreBMais:
    """Busca, inserção com divisão e intervalo inclusivo, sem remoção."""

    def __init__(self, caminho, maximo_chaves=None, capacidade_cache=16):
        if maximo_chaves is not None and (
                type(maximo_chaves) is not int or not 3 <= maximo_chaves <= MAXIMO_CHAVES):
            raise ValueError("Máximo de chaves deve estar entre 3 e 340")
        if type(capacidade_cache) is not int or capacidade_cache <= 0:
            raise ValueError("Capacidade do cache deve ser um inteiro positivo")
        self.arquivo = _ArquivoIndice(caminho, maximo_chaves)
        self.cache = Cache(self.arquivo, capacidade_cache)
        self.maximo_chaves = self.arquivo.capacidade
        if self.arquivo.raiz == 0:
            self.arquivo.raiz = self._novo(_No())
            self.descarrega()

    def _le(self, numero):
        dados = self.cache.fixa(numero)
        try:
            return _No.de_bytes(dados)
        finally:
            self.cache.solta(numero)

    def _grava(self, numero, no):
        dados = no.como_bytes()
        buffer = self.cache.fixa(numero)
        try:
            buffer[:] = dados
        finally:
            self.cache.solta(numero, sujou=True)

    def _novo(self, no):
        numero = self.arquivo.aloca()
        self._grava(numero, no)
        return numero

    def _folha(self, chave):
        no = self._le(self.arquivo.raiz)
        while not no.folha:
            no = self._le(no.valores[bisect_right(no.chaves, chave)])
        return no

    def busca(self, chave):
        """Retorna o RID ou None quando a chave não existe."""
        no = self._folha(chave)
        posicao = bisect_left(no.chaves, chave)
        if posicao < len(no.chaves) and no.chaves[posicao] == chave:
            return no.valores[posicao]
        return None

    def insere(self, chave, rid):
        if type(chave) is not int or not 0 <= chave <= 0xFFFFFFFF:
            raise ValueError("Chave deve ser uint32")
        if not isinstance(rid, (tuple, list)) or len(rid) != 2:
            raise ValueError("RID deve conter página e slot")
        pagina, slot = rid
        if (type(pagina) is not int or not 1 <= pagina <= 0xFFFFFFFF or
                type(slot) is not int or not 0 <= slot < QUANTIDADE_SLOTS):
            raise ValueError("RID inválido")
        raiz = self.arquivo.raiz
        divisao = self._insere(raiz, chave, tuple(rid))
        if divisao is not None:
            separador, direita = divisao
            self.arquivo.raiz = self._novo(_No(False, [separador], [raiz, direita]))

    def _insere(self, numero, chave, rid):
        no = self._le(numero)
        if no.folha:
            posicao = bisect_left(no.chaves, chave)
            if posicao < len(no.chaves) and no.chaves[posicao] == chave:
                raise ValueError("Chave duplicada")
            no.chaves.insert(posicao, chave)
            no.valores.insert(posicao, rid)
        else:
            posicao = bisect_right(no.chaves, chave)
            divisao = self._insere(no.valores[posicao], chave, rid)
            if divisao is None:
                return None
            separador, direita = divisao
            no.chaves.insert(posicao, separador)
            no.valores.insert(posicao + 1, direita)

        if len(no.chaves) <= self.maximo_chaves:
            self._grava(numero, no)
            return None
        return self._divide(numero, no)

    def _divide(self, numero, no):
        """Divide o nó cheio e devolve a chave que será inserida no pai."""
        meio = len(no.chaves) // 2
        separador = no.chaves[meio]
        if no.folha:
            direita = _No(True, no.chaves[meio:], no.valores[meio:], no.proxima)
            no.chaves, no.valores = no.chaves[:meio], no.valores[:meio]
            numero_direita = self._novo(direita)
            no.proxima = numero_direita
        else:
            direita = _No(False, no.chaves[meio + 1:], no.valores[meio + 1:])
            no.chaves, no.valores = no.chaves[:meio], no.valores[:meio + 1]
            numero_direita = self._novo(direita)
        self._grava(numero, no)
        return separador, numero_direita

    def intervalo(self, inicio, fim):
        """Produz (chave, RID) em ordem, incluindo os dois limites."""
        if inicio > fim:
            return
        no = self._folha(inicio)
        posicao = bisect_left(no.chaves, inicio)
        while True:
            for i in range(posicao, len(no.chaves)):
                if no.chaves[i] > fim:
                    return
                yield no.chaves[i], no.valores[i]
            if no.proxima == 0:
                return
            no, posicao = self._le(no.proxima), 0

    def descarrega(self):
        """Grava os nós, a raiz e os metadados antes de reabrir o índice."""
        self.cache.descarrega()
