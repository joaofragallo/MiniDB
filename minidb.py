import os
import struct


TAMANHO_PAGINA = 4096
TAMANHO_CABECALHO = 16
TAMANHO_REGISTRO = 8
QUANTIDADE_SLOTS = (TAMANHO_PAGINA - TAMANHO_CABECALHO) // TAMANHO_REGISTRO

NUMERO_MAGICO = b"MINIDB\0\0"
VERSAO_FORMATO = 1
CABECALHO_ARQUIVO = struct.Struct("<8sHIII")
CABECALHO_PAGINA = struct.Struct("<HHIQ")


class Esquema:
    """Guarda as colunas e monta o formato binário do registro."""

    def __init__(self, colunas):
        self.colunas = tuple(colunas)
        tipos = {"uint32": "I", "int32": "i"}
        try:
            formato = "".join(tipos[tipo] for _, tipo in self.colunas)
        except KeyError as erro:
            raise ValueError("Tipo de coluna não suportado") from erro

        self.formato = "<" + formato
        self.tamanho = struct.calcsize(self.formato)
        if self.tamanho != TAMANHO_REGISTRO:
            raise ValueError("O registro precisa ter 8 bytes")

    def serializa(self, *valores):
        return struct.pack(self.formato, *valores)

    def desserializa(self, dados):
        return struct.unpack(self.formato, dados)


ESQUEMA_ALUNO = Esquema((("id", "uint32"), ("matricula", "uint32")))


def serializa(id_aluno, matricula):
    return ESQUEMA_ALUNO.serializa(id_aluno, matricula)


def desserializa(dados):
    return ESQUEMA_ALUNO.desserializa(dados)


def calcula_offset(numero_pagina, slot=None):
    if numero_pagina < 0:
        raise ValueError("Número da página inválido")
    if slot is None:
        return numero_pagina * TAMANHO_PAGINA
    if slot < 0 or slot >= QUANTIDADE_SLOTS:
        raise ValueError("Slot fora da página")
    return numero_pagina * TAMANHO_PAGINA + TAMANHO_CABECALHO + slot * TAMANHO_REGISTRO


def escreve_pagina(caminho, numero_pagina, dados):
    """Escreve exatamente uma página."""
    if len(dados) != TAMANHO_PAGINA:
        raise ValueError("A página precisa ter 4096 bytes")

    modo = "r+b" if os.path.exists(caminho) else "w+b"
    with open(caminho, modo) as arquivo:
        arquivo.seek(calcula_offset(numero_pagina))
        arquivo.write(dados)


def le_pagina(caminho, numero_pagina):
    """Lê exatamente uma página ou informa que ela está incompleta."""
    with open(caminho, "rb") as arquivo:
        arquivo.seek(calcula_offset(numero_pagina))
        dados = arquivo.read(TAMANHO_PAGINA)

    if len(dados) != TAMANHO_PAGINA:
        raise IOError("Página {} incompleta".format(numero_pagina))
    return dados


class Pagina:
    def __init__(self, dados=None, esquema=ESQUEMA_ALUNO, numero_pagina=None):
        self.esquema = esquema

        if dados is None:
            numero_pagina = 0 if numero_pagina is None else numero_pagina
            dados = bytearray(TAMANHO_PAGINA)
            CABECALHO_PAGINA.pack_into(
                dados, 0, 0, esquema.tamanho, numero_pagina, 0
            )

        if len(dados) != TAMANHO_PAGINA:
            raise ValueError("Dados inválidos para formar uma página")

        quantidade, tamanho, numero, reservado = CABECALHO_PAGINA.unpack_from(dados)
        if quantidade > QUANTIDADE_SLOTS or tamanho != esquema.tamanho:
            raise ValueError("Cabeçalho de página inválido")
        if numero_pagina is not None and numero != numero_pagina:
            raise ValueError("Número da página não confere")

        self.dados = bytearray(dados)
        self.quantidade_registros = quantidade
        self.numero_pagina = numero
        self.reservado = reservado

    def grava_registro(self, slot, id_aluno, matricula):
        if slot < 0 or slot >= QUANTIDADE_SLOTS:
            raise ValueError("Slot fora da página")
        if slot > self.quantidade_registros:
            raise ValueError("Os slots devem ser preenchidos em ordem")

        inicio = TAMANHO_CABECALHO + slot * TAMANHO_REGISTRO
        self.dados[inicio:inicio + TAMANHO_REGISTRO] = self.esquema.serializa(
            id_aluno, matricula
        )
        self.quantidade_registros = max(self.quantidade_registros, slot + 1)
        CABECALHO_PAGINA.pack_into(
            self.dados,
            0,
            self.quantidade_registros,
            self.esquema.tamanho,
            self.numero_pagina,
            self.reservado,
        )

    def insere(self, registro):
        if self.quantidade_registros == QUANTIDADE_SLOTS:
            raise ValueError("Página cheia")
        slot = self.quantidade_registros
        self.grava_registro(slot, *registro)
        return slot

    def le_registro(self, slot):
        if slot < 0 or slot >= self.quantidade_registros:
            raise ValueError("Slot não ocupado")
        inicio = TAMANHO_CABECALHO + slot * TAMANHO_REGISTRO
        return self.esquema.desserializa(
            self.dados[inicio:inicio + TAMANHO_REGISTRO]
        )

    def como_bytes(self):
        return bytes(self.dados)


class Arquivo:
    """Cuida da página 0 e das páginas de dados."""

    def __init__(self, caminho):
        self.caminho = caminho
        self.leituras = 0

        if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
            self.quantidade_paginas = 1
            self.primeira_pagina_livre = 0
            self._salva_metadados()
        else:
            tamanho = os.path.getsize(caminho)
            if tamanho % TAMANHO_PAGINA != 0:
                raise ValueError("Arquivo com página incompleta")
            dados = le_pagina(caminho, 0)
            magico, versao, tamanho_pagina, total, primeira_livre = (
                CABECALHO_ARQUIVO.unpack_from(dados)
            )
            if magico != NUMERO_MAGICO or versao != VERSAO_FORMATO:
                raise ValueError("Formato de arquivo inválido")
            if tamanho_pagina != TAMANHO_PAGINA or total != tamanho // TAMANHO_PAGINA:
                raise ValueError("Metadados do arquivo inválidos")
            self.quantidade_paginas = total
            self.primeira_pagina_livre = primeira_livre

    def _salva_metadados(self):
        dados = bytearray(TAMANHO_PAGINA)
        CABECALHO_ARQUIVO.pack_into(
            dados,
            0,
            NUMERO_MAGICO,
            VERSAO_FORMATO,
            TAMANHO_PAGINA,
            self.quantidade_paginas,
            self.primeira_pagina_livre,
        )
        escreve_pagina(self.caminho, 0, dados)

    def _valida_pagina(self, numero_pagina):
        if numero_pagina < 1 or numero_pagina >= self.quantidade_paginas:
            raise ValueError("Página de dados não alocada")

    def aloca(self):
        numero = self.quantidade_paginas
        pagina = Pagina(numero_pagina=numero)
        escreve_pagina(self.caminho, numero, pagina.como_bytes())
        self.quantidade_paginas += 1
        if self.primeira_pagina_livre == 0:
            self.primeira_pagina_livre = numero
        self._salva_metadados()
        return numero

    def le_pagina(self, numero_pagina):
        self._valida_pagina(numero_pagina)
        self.leituras += 1
        return le_pagina(self.caminho, numero_pagina)

    def escreve_pagina(self, numero_pagina, dados):
        self._valida_pagina(numero_pagina)
        pagina = Pagina(dados, numero_pagina=numero_pagina)
        escreve_pagina(self.caminho, numero_pagina, dados)

        if pagina.quantidade_registros < QUANTIDADE_SLOTS:
            if self.primeira_pagina_livre == 0:
                self.primeira_pagina_livre = numero_pagina
        elif self.primeira_pagina_livre == numero_pagina:
            self.primeira_pagina_livre = self._procura_pagina_livre()
        self._salva_metadados()

    def _procura_pagina_livre(self):
        for numero in range(1, self.quantidade_paginas):
            pagina = Pagina(self.le_pagina(numero), numero_pagina=numero)
            if pagina.quantidade_registros < QUANTIDADE_SLOTS:
                return numero
        return 0

    def insere(self, registro):
        if self.primeira_pagina_livre == 0:
            self.aloca()

        numero = self.primeira_pagina_livre
        pagina = Pagina(self.le_pagina(numero), numero_pagina=numero)
        slot = pagina.insere(registro)
        self.escreve_pagina(numero, pagina.como_bytes())
        return numero, slot

    def varre(self):
        for numero in range(1, self.quantidade_paginas):
            pagina = Pagina(self.le_pagina(numero), numero_pagina=numero)
            for slot in range(pagina.quantidade_registros):
                yield (numero, slot), pagina.le_registro(slot)

    def sync(self):
        with open(self.caminho, "r+b") as arquivo:
            arquivo.flush()
            os.fsync(arquivo.fileno())
