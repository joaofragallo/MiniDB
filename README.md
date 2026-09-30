# MiniDB — Banco de Dados II

## Discentes

- Joao Antonio Fragallo Ferreira — 202511140010
- Erick Wilson

Projeto da disciplina de Banco de Dados II. O M1 implementa o armazenamento de
registros de tamanho fixo em um arquivo dividido em páginas.
O M2 acrescenta um cache de páginas em memória.

## O que foi implementado

- leitura e escrita de páginas de 4096 bytes;
- registros de 8 bytes em little-endian;
- cabeçalho de 16 bytes em cada página de dados;
- página 0 com os metadados do arquivo;
- alocação de páginas, inserção, RID e varredura;
- `sync()` para solicitar a persistência das escritas.

No M2:

- `Cache` com capacidade configurável (16 páginas por padrão);
- `fixa()` e `solta()` com contador de fixações;
- LRU, sem expulsar páginas fixadas;
- páginas sujas gravadas na expulsão ou em `descarrega()`;
- contadores `acertos` e `faltas`;
- inserção e varredura pelo cache.

```python
from minidb import Arquivo, Cache

cache = Cache(Arquivo("alunos.db"), capacidade=16)
rid = cache.insere((1, 20260001))
print(list(cache.varre()))
cache.descarrega()
```

Use um único `Cache` por arquivo. Os métodos diretos de `Arquivo` continuam
disponíveis para o M1; durante o uso do cache, faça as operações por ele para
evitar cópias desatualizadas. Chame `descarrega()` antes de encerrar ou reabrir
o banco: `Arquivo.sync()` sozinho não grava os buffers do cache.

Cada registro possui dois inteiros de 4 bytes: `id` e `matricula`. O RID é o par
`(pagina, slot)`. O registro do slot 0 da página 2 começa no byte 8208:

```text
2 * 4096 + 16 + 0 * 8 = 8208
```

## Execução

```bash
python executar.py
```

Para um arquivo novo, a saída é:

```text
Registro: 1 20260001
RID: (2, 0)
Byte inicial: 8208
Páginas: 3
Leituras sem cache (2 varreduras): 4
Leituras da varredura 1: 2
Leituras da varredura 2: 0
Registros: 1
Acertos: 2
Faltas: 2
```

Os testes são executados com:

```bash
python -m unittest discover -s tests -v
```

O arquivo `dados.db` precisa ser removido ou renomeado caso tenha sido criado
por uma versão anterior do projeto.
