import os
import tempfile
import unittest

from minidb import (
    Pagina,
    QUANTIDADE_SLOTS,
    TAMANHO_CABECALHO,
    TAMANHO_PAGINA,
    TAMANHO_REGISTRO,
    calcula_offset,
    escreve_pagina,
    le_pagina,
)


class TesteM1(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = os.path.join(self.pasta.name, "teste.db")

    def tearDown(self):
        self.pasta.cleanup()

    def test_tamanhos_definidos_no_exercicio(self):
        self.assertEqual(TAMANHO_PAGINA, 4096)
        self.assertEqual(TAMANHO_CABECALHO, 16)
        self.assertEqual(TAMANHO_REGISTRO, 8)
        self.assertEqual(QUANTIDADE_SLOTS, 510)

    def test_escreve_e_le_a_mesma_pagina(self):
        dados = b"A" * TAMANHO_PAGINA
        escreve_pagina(self.arquivo, 1, dados)
        self.assertEqual(le_pagina(self.arquivo, 1), dados)

    def test_paginas_ficam_em_posicoes_diferentes(self):
        pagina_1 = b"A" * TAMANHO_PAGINA
        pagina_2 = b"B" * TAMANHO_PAGINA

        escreve_pagina(self.arquivo, 1, pagina_1)
        escreve_pagina(self.arquivo, 2, pagina_2)

        self.assertEqual(le_pagina(self.arquivo, 1), pagina_1)
        self.assertEqual(le_pagina(self.arquivo, 2), pagina_2)

    def test_registro_continua_no_arquivo(self):
        pagina = Pagina()
        pagina.grava_registro(0, 1, 20260001)
        escreve_pagina(self.arquivo, 2, pagina.como_bytes())

        # le_pagina abre o arquivo novamente.
        pagina_lida = Pagina(le_pagina(self.arquivo, 2))
        self.assertEqual(pagina_lida.le_registro(0), (1, 20260001))

    def test_offset_pagina_2_slot_0(self):
        self.assertEqual(calcula_offset(2, 0), 8208)

    def test_nao_aceita_pagina_com_tamanho_errado(self):
        with self.assertRaises(ValueError):
            escreve_pagina(self.arquivo, 0, b"pagina incompleta")


if __name__ == "__main__":
    unittest.main()
