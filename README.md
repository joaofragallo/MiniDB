# MiniDB — Módulo 1

## Discentes

- Joao Antonio Fragallo Ferreira — 202511140010
- Erick Wilson

Projeto da disciplina de Banco de Dados II. O M1 implementa o armazenamento de
registros de tamanho fixo em um arquivo dividido em páginas.

## O que foi implementado

- leitura e escrita de páginas de 4096 bytes;
- registros de 8 bytes em little-endian;
- cabeçalho de 16 bytes em cada página de dados;
- página 0 com os metadados do arquivo;
- alocação de páginas, inserção, RID e varredura;
- `sync()` para solicitar a persistência das escritas.

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
Leituras da varredura: 2
Registros: 1
```

Os testes são executados com:

```bash
python -m unittest discover -s tests -v
```

O arquivo `dados.db` precisa ser removido ou renomeado caso tenha sido criado
por uma versão anterior do projeto.
