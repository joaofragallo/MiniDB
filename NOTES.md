# NOTES.md — M1

## Linguagem

Usamos Python 3. A linguagem permite trabalhar diretamente com arquivos
binários e com `struct`, sem esconder a organização das páginas.

## Decisão de projeto

A principal decisão foi acessar o arquivo sempre por páginas inteiras. Para
alterar um registro, o programa lê os 4096 bytes da página, muda os 8 bytes do
slot e escreve a página novamente. Isso deixa a classe `Pagina` responsável
pelos registros e a classe `Arquivo` responsável pelo arquivo em disco.

## Formato

- página: 4096 bytes;
- cabeçalho: 16 bytes;
- registro: 8 bytes;
- máximo por página: `(4096 - 16) / 8 = 510` registros;
- RID: `(numero_da_pagina, slot)`.

O cabeçalho de uma página de dados guarda a quantidade de registros, o tamanho
do registro, o número da página e 8 bytes reservados. A página 0 guarda o número
mágico, a versão, o tamanho da página, o total de páginas e a primeira página
com espaço.

O esquema do aluno possui as colunas `id` e `matricula`. As duas são inteiros de
4 bytes. O formato `<II` deixa explícito que a ordem dos bytes é little-endian.

## Posição do registro pedido

O registro `(1, 20260001)` foi gravado no slot 0 da página 2:

```text
offset = pagina * 4096 + 16 + slot * 8
offset = 2 * 4096 + 16 + 0 * 8
offset = 8208
```

Ele ocupa os bytes 8208 a 8215.

## Por que o banco gerencia páginas?

O sistema operacional sabe ler e escrever bytes, mas não conhece registros,
RIDs, páginas livres ou páginas alteradas. O banco controla essas informações
para localizar os dados e decidir quando escrever. Ele ainda usa o sistema
operacional para acessar o arquivo, mas dá significado aos bytes.

## `sync()` e encerramento forçado

Fechar um arquivo envia os dados do buffer do Python para o sistema operacional,
mas eles ainda podem estar somente no cache. `sync()` chama `os.fsync()` para
pedir que as escritas sejam persistidas. Sem `sync`, os dados podem continuar
visíveis depois de encerrar apenas o processo, mas não existe a mesma garantia
em uma queda do sistema.

## Medição

Em uma execução nova de `executar.py`, o arquivo possui 3 páginas: metadados na
página 0, página 1 vazia e um registro na página 2. A varredura lê as duas
páginas de dados, portanto realiza 2 leituras e encontra 1 registro.
