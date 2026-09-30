import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from minidb import Arquivo, Cache, Pagina, QUANTIDADE_SLOTS


class TesteCache(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = os.path.join(self.pasta.name, "teste.db")
        self.arq = Arquivo(self.caminho)
        for _ in range(4):
            self.arq.aloca()
        self.cache = Cache(self.arq, capacidade=3)

    def tearDown(self):
        self.pasta.cleanup()

    def acessa(self, n):
        self.cache.fixa(n)
        self.cache.solta(n)

    def test_hit(self):
        buf = self.cache.fixa(1)
        self.cache.solta(1)
        outro = self.cache.fixa(1)
        self.assertIs(outro, buf)
        self.cache.solta(1)
        self.assertEqual(self.arq.leituras, 1)
        self.assertEqual(self.cache.acertos, 1)
        self.assertEqual(self.cache.faltas, 1)

    def test_hit_e_lru(self):
        for n in (1, 2, 3, 1, 4):
            self.acessa(n)
        self.assertEqual(list(self.cache.uso), [3, 1, 4])
        self.assertEqual(self.cache.acertos, 1)
        self.assertEqual(self.cache.faltas, 4)
        self.assertEqual(self.arq.leituras, 4)

    def test_pin(self):
        self.cache.fixa(1)
        self.cache.fixa(1)
        self.cache.solta(1)
        self.cache.fixa(2)
        self.cache.fixa(3)
        with self.assertRaises(RuntimeError):
            self.cache.fixa(4)
        self.cache.solta(2)
        self.acessa(4)
        self.assertIn(1, self.cache.frames)
        self.assertNotIn(2, self.cache.frames)
        self.assertEqual(self.cache.acertos + self.cache.faltas, 6)

    def test_expulsao_suja(self):
        self.cache = Cache(self.arq, capacidade=1)
        dados = self.cache.fixa(1)
        pag = Pagina(dados, numero_pagina=1)
        self.assertIs(pag.dados, dados)
        pag.insere((7, 20260007))
        self.cache.solta(1, sujou=True)
        disco = Pagina(self.arq.le_pagina(1))
        self.assertEqual(disco.quantidade_registros, 0)
        self.acessa(2)
        # Executa a leitura em outro Python, sem usar a memória deste teste.
        codigo = (
            "import sys\n"
            "from minidb import Arquivo, Cache, Pagina\n"
            "arq = Arquivo(sys.argv[1])\n"
            "cache = Cache(arq)\n"
            "pag = Pagina(cache.fixa(1))\n"
            "print(pag.le_registro(0))\n"
            "cache.solta(1)\n"
        )
        pasta = os.path.dirname(os.path.abspath(__file__))
        projeto = os.path.dirname(pasta)
        saida = subprocess.check_output(
            [sys.executable, "-c", codigo, self.caminho],
            cwd=projeto,
            text=True,
        )
        self.assertEqual(saida.strip(), "(7, 20260007)")

    def test_insere_e_salva(self):
        self.cache = Cache(self.arq, capacidade=1)
        for n in range(QUANTIDADE_SLOTS + 1):
            rid = self.cache.insere((n, n + 1))
        self.assertEqual(rid, (2, 0))
        linhas = list(self.cache.varre())
        self.assertEqual(len(linhas), QUANTIDADE_SLOTS + 1)
        self.cache.descarrega()
        self.assertFalse(self.cache.suja)
        arq = Arquivo(self.caminho)
        cache = Cache(arq)
        salvo = list(cache.varre())
        self.assertEqual(salvo, linhas)

    def test_varre_duas_vezes(self):
        self.cache = Cache(self.arq, capacidade=4)
        list(self.cache.varre())
        antes = self.arq.leituras
        list(self.cache.varre())
        self.assertEqual(antes, 4)
        self.assertEqual(self.arq.leituras, antes)

    def test_valida_entrada(self):
        for cap in (0, -1, 1.5):
            with self.assertRaises(ValueError):
                Cache(self.arq, cap)
        with self.assertRaises(ValueError):
            self.cache.solta(1)
        self.acessa(1)
        with self.assertRaises(ValueError):
            self.cache.solta(1)

    def test_erro_na_escrita(self):
        self.cache = Cache(self.arq, capacidade=1)
        self.cache.insere((1, 2))
        # Simula uma falha do disco apenas durante este bloco.
        with patch.object(self.arq, "escreve_pagina", side_effect=OSError):
            with self.assertRaises(OSError):
                self.cache.fixa(2)
        self.assertIn(1, self.cache.suja)
        self.assertIn(1, self.cache.frames)

    def test_libera_pin(self):
        self.cache.insere((1, 2))
        it = self.cache.varre()
        next(it)
        it.close()
        self.assertEqual(self.cache.fixada[1], 0)
        with self.assertRaises(TypeError):
            self.cache.insere((1,))
        self.assertEqual(self.cache.fixada[1], 0)


if __name__ == "__main__":
    unittest.main()
