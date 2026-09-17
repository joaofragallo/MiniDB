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
