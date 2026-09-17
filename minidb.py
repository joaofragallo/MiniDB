import os
import struct


TAMANHO_PAGINA = 4096
TAMANHO_CABECALHO = 16
TAMANHO_REGISTRO = 8
QUANTIDADE_SLOTS = (TAMANHO_PAGINA - TAMANHO_CABECALHO) // TAMANHO_REGISTRO
NUMERO_MAGICO = b"MINIDB01"
CABECALHO_ARQUIVO = struct.Struct("<8sII")
CABECALHO_PAGINA = struct.Struct("<IIII")


class Esquema:
    """Deriva o formato binário a partir de colunas (nome, tipo)."""

    def __init__(self, colunas):
        self.colunas = tuple(colunas)
        tipos = {"uint32": "I", "int32": "i"}
        if not self.colunas or len({nome for nome, _ in self.colunas}) != len(self.colunas):
            raise ValueError("O esquema precisa de colunas com nomes distintos")
        try:
            self.formato = "<" + "".join(tipos[tipo] for _, tipo in self.colunas)
        except KeyError as erro:
            raise ValueError("Tipo de coluna não suportado") from erro
        self._estrutura = struct.Struct(self.formato)
        self.tamanho = self._estrutura.size
        if self.tamanho != TAMANHO_REGISTRO:
            raise ValueError("O registro precisa ter exatamente 8 bytes")

    def serializa(self, *valores):
        return self._estrutura.pack(*valores)

    def desserializa(self, dados):
        return self._estrutura.unpack(dados)


ESQUEMA_ALUNO = Esquema((("id", "uint32"), ("matricula", "uint32")))


def serializa(id_aluno, matricula):
    return ESQUEMA_ALUNO.serializa(id_aluno, matricula)


def desserializa(dados):
    return ESQUEMA_ALUNO.desserializa(dados)


def calcula_offset(numero_pagina, slot=None):
    """Calcula a posição de uma página ou de um registro no arquivo."""
    if numero_pagina < 0:
        raise ValueError("O número da página não pode ser negativo")
    if slot is None:
        return numero_pagina * TAMANHO_PAGINA
    if slot < 0 or slot >= QUANTIDADE_SLOTS:
        raise ValueError("Slot fora dos limites da página")

    return (
        numero_pagina * TAMANHO_PAGINA
        + TAMANHO_CABECALHO
        + slot * TAMANHO_REGISTRO
    )


def escreve_pagina(caminho, numero_pagina, dados):
    """Escreve uma página completa no arquivo."""
    if len(dados) != TAMANHO_PAGINA:
        raise ValueError("A página precisa ter exatamente 4096 bytes")

    offset = calcula_offset(numero_pagina)
    modo = "r+b" if os.path.exists(caminho) else "w+b"

    with open(caminho, modo) as arquivo:
        arquivo.seek(offset)
        arquivo.write(dados)


def le_pagina(caminho, numero_pagina):
    """Lê uma página. A parte que ainda não existe é completada com zeros."""
    offset = calcula_offset(numero_pagina)
    if not os.path.exists(caminho):
        return bytes(TAMANHO_PAGINA)

    with open(caminho, "rb") as arquivo:
        arquivo.seek(offset)
        dados = arquivo.read(TAMANHO_PAGINA)

    if len(dados) < TAMANHO_PAGINA:
        dados += bytes(TAMANHO_PAGINA - len(dados))

    return dados


class Pagina:
    def __init__(self, dados=None, esquema=ESQUEMA_ALUNO):
        if dados is None:
            dados = bytes(TAMANHO_PAGINA)
        if len(dados) != TAMANHO_PAGINA:
            raise ValueError("Dados inválidos para formar uma página")

        # bytearray é usado porque bytes não pode ser alterado.
        self.dados = bytearray(dados)
        self.esquema = esquema
        quantidade, reservado_1, reservado_2, reservado_3 = CABECALHO_PAGINA.unpack_from(dados)
        if quantidade > QUANTIDADE_SLOTS or any((reservado_1, reservado_2, reservado_3)):
            raise ValueError("Cabeçalho de página inválido")
        self.quantidade_registros = quantidade

    def _inicio_do_slot(self, slot):
        return calcula_offset(0, slot)

    def grava_registro(self, slot, id_aluno, matricula):
        inicio = self._inicio_do_slot(slot)
        if slot > self.quantidade_registros:
            raise ValueError("Os registros devem ocupar slots consecutivos")
        registro = self.esquema.serializa(id_aluno, matricula)
        self.dados[inicio:inicio + TAMANHO_REGISTRO] = registro
        self.quantidade_registros = max(self.quantidade_registros, slot + 1)
        CABECALHO_PAGINA.pack_into(self.dados, 0, self.quantidade_registros, 0, 0, 0)

    def le_registro(self, slot):
        inicio = self._inicio_do_slot(slot)
        registro = self.dados[inicio:inicio + TAMANHO_REGISTRO]
        return self.esquema.desserializa(registro)

    def como_bytes(self):
        return bytes(self.dados)


class Arquivo:
    """Gerencia páginas alocadas; a página 0 identifica o formato do arquivo."""

    def __init__(self, caminho):
        self.caminho = caminho
        self.leituras = 0
        if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
            dados = bytearray(TAMANHO_PAGINA)
            CABECALHO_ARQUIVO.pack_into(dados, 0, NUMERO_MAGICO, TAMANHO_PAGINA, 1)
            escreve_pagina(caminho, 0, dados)
        tamanho = os.path.getsize(caminho)
        if tamanho % TAMANHO_PAGINA:
            raise ValueError("Arquivo contém uma página incompleta")
        dados = le_pagina(caminho, 0)
        self.leituras += 1
        magico, tamanho_pagina, versao = CABECALHO_ARQUIVO.unpack_from(dados)
        if (magico, tamanho_pagina, versao) != (NUMERO_MAGICO, TAMANHO_PAGINA, 1):
            raise ValueError("Cabeçalho do arquivo inválido ou versão incompatível")

    @property
    def quantidade_paginas(self):
        # Inclui a página 0; não duplica o tamanho do arquivo nos metadados.
        tamanho = os.path.getsize(self.caminho)
        if tamanho % TAMANHO_PAGINA:
            raise ValueError("Arquivo contém uma página incompleta")
        return tamanho // TAMANHO_PAGINA

    def _valida_pagina(self, numero_pagina):
        if numero_pagina < 1 or numero_pagina >= self.quantidade_paginas:
            raise ValueError("Página de dados não alocada")

    def aloca(self):
        numero_pagina = self.quantidade_paginas
        escreve_pagina(self.caminho, numero_pagina, Pagina().como_bytes())
        return numero_pagina

    def le_pagina(self, numero_pagina):
        self._valida_pagina(numero_pagina)
        dados = le_pagina(self.caminho, numero_pagina)
        self.leituras += 1
        return dados

    def escreve_pagina(self, numero_pagina, dados):
        self._valida_pagina(numero_pagina)
        escreve_pagina(self.caminho, numero_pagina, dados)

    def varre(self):
        """Produz (RID, registro), lendo cada página de dados uma única vez."""
        for numero in range(1, self.quantidade_paginas):
            pagina = Pagina(self.le_pagina(numero))
            for slot in range(pagina.quantidade_registros):
                yield (numero, slot), pagina.le_registro(slot)

    def sync(self):
        """Solicita ao sistema operacional a persistência das escritas anteriores."""
        with open(self.caminho, "r+b") as arquivo:
            arquivo.flush()
            os.fsync(arquivo.fileno())
