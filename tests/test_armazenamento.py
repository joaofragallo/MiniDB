import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from minidb import (
    Arquivo, Esquema, Pagina, NUMERO_MAGICO, QUANTIDADE_SLOTS,
    calcula_offset, serializa, desserializa, le_pagina, escreve_pagina,
)


class TesteArmazenamento(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.caminho = os.path.join(self.pasta.name, "teste.db")

    def test_serializacao_little_endian_e_limites(self):
        self.assertEqual(serializa(1, 0x12345678), b"\x01\0\0\0\x78\x56\x34\x12")
        self.assertEqual(desserializa(serializa(0, 2**32 - 1)), (0, 2**32 - 1))
        for valores in ((-1, 0), (0, 2**32), (1.5, 0)):
            with self.assertRaises(struct.error):
                serializa(*valores)
        with self.assertRaises(struct.error):
            desserializa(b"curto")

    def test_formato_derivado_das_colunas(self):
        esquema = Esquema((("codigo", "int32"), ("valor", "uint32")))
        self.assertEqual(esquema.formato, "<iI")
        self.assertEqual(esquema.tamanho, 8)
        pagina = Pagina(esquema=esquema)
        pagina.grava_registro(0, -7, 42)
        self.assertEqual(Pagina(pagina.como_bytes(), esquema).le_registro(0), (-7, 42))
        for colunas in ((), (("a", "uint32"),), (("a", "texto"),),
                        (("a", "uint32"), ("a", "uint32"))):
            with self.assertRaises(ValueError):
                Esquema(colunas)

    def test_cabecalho_e_pagina_cheia(self):
        pagina = Pagina()
        for slot in range(QUANTIDADE_SLOTS):
            pagina.grava_registro(slot, slot, slot + 1)
        pagina.grava_registro(0, 99, 100)
        dados = pagina.como_bytes()
        self.assertEqual(len(dados), 4096)
        self.assertEqual(struct.unpack("<IIII", dados[:16]), (510, 0, 0, 0))
        recuperada = Pagina(dados)
        self.assertEqual(recuperada.quantidade_registros, 510)
        self.assertEqual(recuperada.le_registro(509), (509, 510))
        with self.assertRaises(ValueError):
            pagina.grava_registro(510, 0, 0)
        with self.assertRaises(ValueError):
            Pagina().grava_registro(1, 1, 1)

    def test_alocacao_reabertura_e_varredura(self):
        arquivo = Arquivo(self.caminho)
        self.assertEqual(arquivo.quantidade_paginas, 1)
        self.assertEqual(struct.unpack("<8sII", le_pagina(self.caminho, 0)[:16]),
                         (NUMERO_MAGICO, 4096, 1))
        self.assertEqual(arquivo.aloca(), 1)
        self.assertEqual(arquivo.aloca(), 2)
        pagina = Pagina()
        pagina.grava_registro(0, 0, 0)
        pagina.grava_registro(1, 1, 20260001)
        arquivo.escreve_pagina(2, pagina.como_bytes())
        arquivo.sync()
        recuperado = Arquivo(self.caminho)
        self.assertEqual(recuperado.quantidade_paginas, 3)
        antes = recuperado.leituras
        self.assertEqual(list(recuperado.varre()), [((2, 0), (0, 0)), ((2, 1), (1, 20260001))])
        self.assertEqual(recuperado.leituras - antes, 2)
        self.assertEqual(recuperado.aloca(), 3)

    def test_limites_e_metadados_protegidos(self):
        arquivo = Arquivo(self.caminho)
        for numero in (-1, 0, 1):
            with self.assertRaises(ValueError):
                arquivo.le_pagina(numero)
            with self.assertRaises(ValueError):
                arquivo.escreve_pagina(numero, bytes(4096))
        with self.assertRaises(ValueError):
            le_pagina(self.caminho, -1)
        with self.assertRaises(ValueError):
            escreve_pagina(self.caminho, -1, bytes(4096))
        self.assertEqual(calcula_offset(2), 8192)
        for slot in (-1, 510):
            with self.assertRaises(ValueError):
                calcula_offset(2, slot)

    def test_rejeita_arquivo_invalido_ou_truncado(self):
        for dados in (b"incompleto", bytes(4096),
                      struct.pack("<8sII", NUMERO_MAGICO, 2048, 1) + bytes(4080),
                      struct.pack("<8sII", NUMERO_MAGICO, 4096, 2) + bytes(4080)):
            with open(self.caminho, "wb") as arquivo:
                arquivo.write(dados)
            with self.assertRaises(ValueError):
                Arquivo(self.caminho)
        with self.assertRaises(ValueError):
            Pagina(struct.pack("<IIII", 511, 0, 0, 0) + bytes(4080))

    def test_sync_solicita_fsync_e_propaga_falha(self):
        arquivo = Arquivo(self.caminho)
        with patch("minidb.os.fsync") as fsync:
            arquivo.sync()
            fsync.assert_called_once()
        with patch("minidb.os.fsync", side_effect=OSError("falha de disco")):
            with self.assertRaises(OSError):
                arquivo.sync()

    def test_sync_sobrevive_ao_encerramento_forcado(self):
        marcador = os.path.join(self.pasta.name, "pronto")
        codigo = """
import pathlib, sys, time
from minidb import Arquivo, Pagina
arquivo = Arquivo(sys.argv[1])
numero = arquivo.aloca()
pagina = Pagina()
pagina.grava_registro(0, 1, 20260001)
arquivo.escreve_pagina(numero, pagina.como_bytes())
arquivo.sync()
pathlib.Path(sys.argv[2]).touch()
time.sleep(60)
"""
        processo = subprocess.Popen([sys.executable, "-c", codigo, self.caminho, marcador],
                                    cwd=str(Path(__file__).resolve().parents[1]))
        try:
            limite = time.monotonic() + 10
            while not os.path.exists(marcador) and time.monotonic() < limite:
                if processo.poll() is not None:
                    self.fail("Processo terminou antes de sync")
                time.sleep(0.02)
            self.assertTrue(os.path.exists(marcador), "Timeout aguardando sync")
        finally:
            if processo.poll() is None:
                processo.kill()
            processo.wait(timeout=5)
        arquivo = Arquivo(self.caminho)
        self.assertEqual(arquivo.quantidade_paginas, 2)
        self.assertEqual(list(arquivo.varre()), [((1, 0), (1, 20260001))])
