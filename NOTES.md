# NOTES.md — M1

## Linguagem escolhida

Python 3.

Escolhemos Python porque, neste módulo, o objetivo principal é entender a
organização do arquivo em páginas, offsets, registros e RIDs. Python reduz o
código incidental de gerenciamento de memória e permite concentrar a
implementação nessas estruturas.

## Formato usado

- Tamanho de página: 4096 bytes
- Cabeçalho de cada página: 16 bytes
- Tamanho de registro: 8 bytes
- Registro: dois inteiros de 4 bytes (`id` e `matricula`)
- RID: par `(pagina, slot)`

## Decisão de projeto mais importante

A decisão principal foi tratar o arquivo como uma sequência de páginas de
tamanho fixo e nunca escrever um registro diretamente "solto" no arquivo.
Para alterar um registro, lemos a página inteira, modificamos os 8 bytes do
slot desejado e escrevemos novamente os 4096 bytes da página.

Isso mantém a abstração pedida pela disciplina: o disco é acessado em páginas,
e as camadas superiores trabalham com registros e RIDs.

Outra decisão foi fixar explicitamente a serialização em **little-endian**, por
meio do formato `"<II"` de `struct`. Dessa forma, o arquivo não depende da
ordem de bytes nativa da máquina em que o programa for executado. Cada campo é
um inteiro sem sinal de 32 bits, portanto o registro sempre mede 8 bytes.

Ao ler uma página ainda não existente, devolvemos 4096 bytes zerados. Isso
permite materializar diretamente uma página distante (por exemplo, a página 2)
e ainda manter o contrato de que toda leitura de página retorna exatamente
4096 bytes.

## Em que byte do arquivo foi parar o registro?

O exercício pede o registro no slot 0 da página 2.

A posição inicial de um registro é:

    offset = pagina * 4096 + 16 + slot * 8

Substituindo `(pagina=2, slot=0)`:

    offset = 2 * 4096 + 16 + 0 * 8
    offset = 8192 + 16
    offset = 8208

Portanto, o registro começa no byte **8208** do arquivo `dados.db`.

Os 8 bytes do registro ocupam as posições 8208 a 8215, inclusive.

## Quantos slots cabem em uma página?

Depois dos 16 bytes de cabeçalho restam:

    4096 - 16 = 4080 bytes

Como cada registro ocupa 8 bytes:

    4080 / 8 = 510 registros

Logo, os slots válidos são de 0 a 509.

## Complemento de 17/09: esquema e cabeçalhos

A arquitetura continua concentrada em `minidb.py`: funções de acesso binário,
`Pagina` para os registros, `Esquema` para sua representação e `Arquivo` para
gerenciar o banco. O JanusDB foi consultado como referência conceitual de
páginas e deslocamentos, sem copiar sua implementação:
https://github.com/Anders0nlima/JanusDB/tree/a2c5dce197ae4a92255f4428dda8bc5edfe9ae20

O esquema padrão contém `id` e `matricula`, ambos `uint32`. O formato `<II`
é derivado dessas colunas. São aceitos também campos `int32`, mantendo o total
de 8 bytes. O esquema é um objeto Python, não um catálogo persistido no arquivo;
o gerenciador e sua varredura usam o esquema padrão de aluno.

Os primeiros 16 bytes da página 0 usam `<8sII`:

| Bytes | Conteúdo |
| --- | --- |
| 0–7 | Número mágico `MINIDB01` |
| 8–11 | Tamanho de página: 4096 |
| 12–15 | Versão do formato: 1 |

Nas páginas de dados, o cabeçalho usa `<IIII`: quantidade de registros seguida
de três inteiros reservados, obrigatoriamente zero. Os registros ocupam slots
consecutivos a partir de 0; pode-se acrescentar no próximo slot ou substituir
um existente. Não há exclusão ou slots esparsos nesta etapa. Assim, um registro
`(0, 0)` é válido e não se confunde com uma página vazia durante a varredura.

O deslocamento de página e de registro passa por `calcula_offset`. As funções
de baixo nível mantêm a leitura preenchida com zeros para compatibilidade.
`Arquivo` valida o número mágico, tamanho, versão e alinhamento do arquivo,
impede acesso a páginas não alocadas e protege a página 0 contra escrita pela
API de páginas de dados. Arquivos antigos não são migrados automaticamente.

## Alocação e leituras da varredura

`aloca()` acrescenta uma página de 4096 bytes, inicialmente zerada, e devolve
seu número. A contagem vem do tamanho do arquivo dividido por 4096, incluindo
a página 0, e continua correta após reabrir. Não há suporte a escritores
concorrentes.

Em uma execução nova de `executar.py`, o arquivo tem **3 páginas (12288 bytes)**:
metadados na 0, página 1 vazia e um registro na página 2. A varredura completa
faz **2 leituras**, uma por página de dados, e encontra **1 registro**.
A leitura dos metadados na abertura é contabilizada em `leituras`, mas fica
fora da diferença medida antes e depois da varredura. O contador mede chamadas
de leitura de páginas, não acessos físicos ao dispositivo ou consultas de tamanho.

## sync e encerramento forçado

Cada escrita fecha o arquivo, descarregando o buffer Python para o sistema
operacional. `sync()` abre o mesmo arquivo, chama `flush()` e `os.fsync()` e
propaga eventuais erros. Depois de seu retorno com sucesso, as escritas anteriores
foram submetidas à sincronização do sistema operacional. Alterações feitas só
em um objeto `Pagina` precisam primeiro de `escreve_pagina`.

O teste inicia um subprocesso, grava um registro, sincroniza, sinaliza que
terminou e aguarda. O processo pai o encerra à força e reabre o banco para
conferir a contagem e o registro. Em Unix, `Popen.kill()` usa SIGKILL
(`kill -9`); no Windows usa TerminateProcess. O teste não simula queda de energia.

Sem `sync`, dados podem continuar visíveis após matar apenas o processo,
porque o cache do sistema operacional continua vivo; isso não comprova
persistência em uma queda do sistema. Não há WAL, transações, garantia de escrita
atômica de página ou sincronização do diretório de criação. Uma interrupção
durante uma escrita pode deixar um arquivo parcial; um tamanho não múltiplo
de 4096 é rejeitado na reabertura.

Validação: `python -m unittest discover -s tests -v` — 14 testes, incluindo os
6 testes originais e 8 testes adicionais.
