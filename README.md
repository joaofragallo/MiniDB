# MiniDB - Módulo 1
### Discentes 

  * Joao Antonio Fragallo Ferreira - 202511140010
  * Erick Wilson

Este é o primeiro módulo do projeto da disciplina de Banco de Dados II. Neste
módulo ainda não existe SQL. A ideia é entender como os dados podem ser
guardados em posições específicas de um arquivo binário.

## Formato usado

- página: 4096 bytes;
- cabeçalho da página: 16 bytes;
- registro: 8 bytes;
- campos do registro: `id` e `matricula`, com 4 bytes cada;
- RID: `(numero da pagina, slot)`.

O arquivo é dividido em páginas. Dentro de cada página, os primeiros 16 bytes
guardam o cabeçalho e depois começam os slots dos registros. A página 0
é reservada aos metadados do arquivo; os dados começam na página 1.

Para descobrir a posição de um registro no arquivo foi usada esta conta:

```text
pagina * 4096 + 16 + slot * 8
```

Por exemplo, para o RID `(2, 0)`:

```text
2 * 4096 + 16 + 0 * 8 = 8208
```

## Arquivos principais

- `minidb.py`: leitura e escrita de páginas, `Pagina`, `Esquema` e `Arquivo`;
- `executar.py`: grava e recupera o registro pedido no exercício;
- `tests/test_m1.py`: testes do módulo.
- `tests/test_armazenamento.py`: esquema, cabeçalhos, alocação, varredura e persistência.

## Como executar

```bash
python3 executar.py
```

Resultado esperado:

```text
Registro recuperado:
id: 1
matricula: 20260001
RID: (2, 0)
Byte inicial: 8208
Páginas no arquivo: 3
Leituras da varredura: 2
Registros encontrados: 1
```

Para rodar os testes:

```bash
python3 -m unittest discover -s tests -v
```

O resultado acima considera um arquivo novo. Executar novamente atualiza o
mesmo registro, sem alocar novas páginas. Arquivos da versão anterior, sem
número mágico, são rejeitados por `Arquivo`: preserve o arquivo antigo e use
outro caminho em `ARQUIVO` para criar um banco no novo formato.

`Esquema` recebe pares `(nome, tipo)`, com tipos `uint32` ou `int32`, e deriva
um formato little-endian de exatamente 8 bytes. `serializa` e `desserializa`
usam o esquema padrão de aluno. `Pagina` usa esse objeto para converter registros.

`Arquivo.aloca()` grava uma página vazia e retorna seu número.
`quantidade_paginas` inclui a página 0; `varre()` retorna pares `(RID, registro)`
e incrementa `leituras` uma vez por página de dados, inclusive páginas vazias.
`sync()` solicita a persistência com `os.fsync`. Consulte `NOTES.md` para os
limites dessa garantia e o formato dos cabeçalhos.
