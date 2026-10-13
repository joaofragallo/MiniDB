# MiniDB — Banco de Dados II

## Discentes

- Joao Antonio Fragallo Ferreira — 202511140010
- Erick Wilson

Projeto da disciplina de Banco de Dados II. O M1 implementa o armazenamento de
registros de tamanho fixo em um arquivo dividido em páginas.
O M2 acrescenta um cache de páginas em memória.
O M3 acrescenta um índice B+ em `arvore_bmais.py`.

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

### M3 — Índice B+

O índice guarda chaves `uint32` únicas e seus RIDs em um arquivo separado.
Suporta busca, inserção com divisão e intervalos inclusivos, sem remoção.
Cada nó ocupa uma página de 4096 bytes e usa o mesmo `Cache` do M2.

```python
from minidb import Arquivo, Cache, Pagina
from arvore_bmais import ArvoreBMais

dados = Cache(Arquivo("alunos.db"))
indice = ArvoreBMais("alunos.idx")

# Use uma chave que ainda não exista no índice.
rid = dados.insere((42, 20260042))
indice.insere(42, rid)

rid = indice.busca(42)  # None se não existir
if rid is not None:
    numero, slot = rid
    buffer = dados.fixa(numero)
    try:
        print(Pagina(buffer).le_registro(slot))
    finally:
        dados.solta(numero)

print(list(indice.intervalo(20, 65)))  # pares (chave, RID), em ordem
dados.descarrega()
indice.descarrega()
```

O índice é mantido explicitamente: `dados.insere()` não atualiza o índice.
Para registros existentes, use `dados.varre()` e insira cada `registro[0]`
com seu RID em um índice novo. IDs repetidos são rejeitados.
Use um único objeto de índice por arquivo e descarregue antes de reabrir.
Não há transações entre os arquivos de dados e de índice.
Para reproduzir as divisões do slide, crie um índice novo com
`ArvoreBMais("exercicio.idx", maximo_chaves=3)`; o padrão é 340.

### Exemplo do M1 e M2

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
