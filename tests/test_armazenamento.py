import os
import struct
import tempfile
import unittest

from minidb import (
    Arquivo,
    CABECALHO_ARQUIVO,
    Esquema,
    NUMERO_MAGICO,
    Pagina,
    QUANTIDADE_SLOTS,
    VERSAO_FORMATO,
    desserializa,
    le_pagina,
    serializa,
)


class TesteArmazenamento(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = os.path.join(self.pasta.name, "teste.db")

    def tearDown(self):
        self.pasta.cleanup()

    def test_serializacao_little_endian(self):
        dados = serializa(1, 0x12345678)
        self.assertEqual(dados, b"\x01\x00\x00\x00\x78\x56\x34\x12")
        self.assertEqual(desserializa(dados), (1, 0x12345678))

        esquema = Esquema((("codigo", "int32"), ("valor", "uint32")))
        self.assertEqual(esquema.formato, "<iI")

    def test_cabecalho_da_pagina(self):
        pagina = Pagina(numero_pagina=2)
        pagina.grava_registro(0, 1, 20260001)
        dados = pagina.como_bytes()

        self.assertEqual(struct.unpack("<HHIQ", dados[:16]), (1, 8, 2, 0))
        self.assertEqual(dados[:8], b"\x01\x00\x08\x00\x02\x00\x00\x00")
        self.assertEqual(Pagina(dados, numero_pagina=2).le_registro(0), (1, 20260001))

    def test_alocacao_e_metadados(self):
        arquivo = Arquivo(self.arquivo)
        self.assertEqual(arquivo.aloca(), 1)
        self.assertEqual(arquivo.aloca(), 2)

        metadados = CABECALHO_ARQUIVO.unpack_from(le_pagina(self.arquivo, 0))
        self.assertEqual(
            metadados,
            (NUMERO_MAGICO, VERSAO_FORMATO, 4096, 3, 1),
        )

        reaberto = Arquivo(self.arquivo)
        self.assertEqual(reaberto.quantidade_paginas, 3)

    def test_insercao_cria_outra_pagina_quando_precisa(self):
        arquivo = Arquivo(self.arquivo)
        numero = arquivo.aloca()
        pagina = Pagina(arquivo.le_pagina(numero), numero_pagina=numero)
        for slot in range(QUANTIDADE_SLOTS):
            pagina.grava_registro(slot, slot, slot + 1)
        arquivo.escreve_pagina(numero, pagina.como_bytes())

        rid = arquivo.insere((510, 511))
        self.assertEqual(rid, (2, 0))

        antes = arquivo.leituras
        registros = list(arquivo.varre())
        self.assertEqual(len(registros), 511)
        self.assertEqual(arquivo.leituras - antes, 2)

    def test_leitura_incompleta_falha(self):
        with self.assertRaises(FileNotFoundError):
            le_pagina(self.arquivo, 0)

        with open(self.arquivo, "wb") as arquivo:
            arquivo.write(b"poucos bytes")
        with self.assertRaises(IOError):
            le_pagina(self.arquivo, 0)

    def test_sync_e_reabertura(self):
        arquivo = Arquivo(self.arquivo)
        rid = arquivo.insere((1, 20260001))
        arquivo.sync()

        reaberto = Arquivo(self.arquivo)
        self.assertEqual(rid, (1, 0))
        self.assertEqual(list(reaberto.varre()), [((1, 0), (1, 20260001))])


if __name__ == "__main__":
    unittest.main()
