import os
import struct


TAMANHO_PAGINA = 4096
TAMANHO_CABECALHO = 16
TAMANHO_REGISTRO = 8
QUANTIDADE_SLOTS = (TAMANHO_PAGINA - TAMANHO_CABECALHO) // TAMANHO_REGISTRO


def calcula_offset(numero_pagina, slot):
    """Calcula a posição de um registro dentro do arquivo."""
    if numero_pagina < 0:
        raise ValueError("O número da página não pode ser negativo")
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

    modo = "r+b" if os.path.exists(caminho) else "w+b"

    with open(caminho, modo) as arquivo:
        arquivo.seek(numero_pagina * TAMANHO_PAGINA)
        arquivo.write(dados)


def le_pagina(caminho, numero_pagina):
    """Lê uma página. A parte que ainda não existe é completada com zeros."""
    if not os.path.exists(caminho):
        return bytes(TAMANHO_PAGINA)

    with open(caminho, "rb") as arquivo:
        arquivo.seek(numero_pagina * TAMANHO_PAGINA)
        dados = arquivo.read(TAMANHO_PAGINA)

    if len(dados) < TAMANHO_PAGINA:
        dados += bytes(TAMANHO_PAGINA - len(dados))

    return dados


class Pagina:
    def __init__(self, dados=None):
        if dados is None:
            dados = bytes(TAMANHO_PAGINA)
        if len(dados) != TAMANHO_PAGINA:
            raise ValueError("Dados inválidos para formar uma página")

        # bytearray é usado porque bytes não pode ser alterado.
        self.dados = bytearray(dados)

    def _inicio_do_slot(self, slot):
        if slot < 0 or slot >= QUANTIDADE_SLOTS:
            raise ValueError("Slot fora dos limites da página")
        return TAMANHO_CABECALHO + slot * TAMANHO_REGISTRO

    def grava_registro(self, slot, id_aluno, matricula):
        inicio = self._inicio_do_slot(slot)
        registro = struct.pack("<II", id_aluno, matricula)
        self.dados[inicio:inicio + TAMANHO_REGISTRO] = registro

    def le_registro(self, slot):
        inicio = self._inicio_do_slot(slot)
        registro = self.dados[inicio:inicio + TAMANHO_REGISTRO]
        return struct.unpack("<II", registro)

    def como_bytes(self):
        return bytes(self.dados)
