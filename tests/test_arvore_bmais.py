import os
import random
import tempfile
import unittest

from arvore_bmais import ArvoreBMais
from minidb import Arquivo, Cache, Pagina


class TesteArvoreBMais(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.caminho = os.path.join(self.pasta.name, "alunos.idx")
        self.arvore = ArvoreBMais(self.caminho, maximo_chaves=3, capacidade_cache=1)

    def test_exercicios_do_slide(self):
        for chave in (10, 20, 5, 30, 25, 40, 15):
            self.arvore.insere(chave, (1, chave))
        raiz = self.arvore._le(self.arvore.arquivo.raiz)
        self.assertEqual(raiz.chaves, [20, 30])
        self.assertEqual([self.arvore._le(n).chaves for n in raiz.valores],
                         [[5, 10, 15], [20, 25], [30, 40]])
        for chave in (35, 45, 50, 55):
            self.arvore.insere(chave, (1, chave))
        raiz = self.arvore._le(self.arvore.arquivo.raiz)
        self.assertEqual(raiz.chaves, [40])
        self.assertTrue(all(not self.arvore._le(n).folha for n in raiz.valores))
        self.assertEqual(list(self.arvore.intervalo(12, 33)),
                         [(c, (1, c)) for c in (15, 20, 25, 30)])

    def test_divisoes_reabertura_e_invariantes(self):
        chaves = list(range(400))
        random.Random(42).shuffle(chaves)
        for chave in chaves:
            self.arvore.insere(chave, (1, chave))
        self.arvore.descarrega()
        arvore = ArvoreBMais(self.caminho, capacidade_cache=1)
        self.assertEqual(arvore.maximo_chaves, 3)
        for chave in chaves:
            self.assertEqual(arvore.busca(chave), (1, chave))
        self.assertIsNone(arvore.busca(999))
        self.assertEqual(list(arvore.intervalo(-1, 999)),
                         [(c, (1, c)) for c in range(400)])
        profundidades = set()

        def confere(numero, nivel):
            no = arvore._le(numero)
            self.assertLessEqual(len(no.chaves), 3)
            self.assertEqual(no.chaves, sorted(set(no.chaves)))
            if no.folha:
                profundidades.add(nivel)
                return no.chaves[0], no.chaves[-1]
            self.assertEqual(len(no.valores), len(no.chaves) + 1)
            limites = [confere(n, nivel + 1) for n in no.valores]
            for i, chave in enumerate(no.chaves):
                self.assertLess(limites[i][1], chave)
                self.assertEqual(limites[i + 1][0], chave)
            return limites[0][0], limites[-1][1]

        confere(arvore.arquivo.raiz, 0)
        self.assertEqual(len(profundidades), 1)
        self.assertTrue(all(p == 0 for p in arvore.cache.fixada.values()))

    def test_vazia_duplicadas_e_limites(self):
        self.assertIsNone(self.arvore.busca(1))
        self.assertEqual(list(self.arvore.intervalo(0, 10)), [])
        self.arvore.insere(0, (1, 0))
        self.arvore.insere(0xFFFFFFFF, (2, 509))
        with self.assertRaises(ValueError):
            self.arvore.insere(0, (3, 1))
        self.assertEqual(self.arvore.busca(0), (1, 0))
        for chave, rid in ((-1, (1, 0)), (2**32, (1, 0)), (2, (0, 0)),
                           (2, (1, 510)), (2, (1,))):
            with self.assertRaises(ValueError):
                self.arvore.insere(chave, rid)
        self.assertEqual(list(self.arvore.intervalo(10, 0)), [])

    def test_capacidade_real_e_registro_do_m1(self):
        indice = ArvoreBMais(os.path.join(self.pasta.name, "real.idx"))
        for chave in range(700):
            indice.insere(chave, (1 + chave // 510, chave % 510))
        indice.descarrega()
        indice = ArvoreBMais(indice.arquivo.caminho)
        self.assertEqual(indice.busca(699), (2, 189))
        dados = Cache(Arquivo(os.path.join(self.pasta.name, "alunos.db")))
        rid = dados.insere((42, 20260042))
        self.arvore.insere(42, rid)
        numero, slot = self.arvore.busca(42)
        buffer = dados.fixa(numero)
        try:
            self.assertEqual(Pagina(buffer).le_registro(slot), (42, 20260042))
        finally:
            dados.solta(numero)
        dados.descarrega()


if __name__ == "__main__":
    unittest.main()
