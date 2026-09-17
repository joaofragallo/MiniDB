# Anotações do M1

## Decisão tomada

Eu decidi manter a leitura e a escrita do arquivo separadas da classe
`Pagina`. As funções `le_pagina` e `escreve_pagina` cuidam apenas do arquivo.
A classe `Pagina` cuida de colocar e retirar registros nos slots.

Fiz assim porque ficou mais fácil enxergar duas coisas diferentes: primeiro a
página existe como um conjunto de bytes na memória e depois ela é gravada em
uma posição do arquivo. Também usei `bytearray` dentro da classe porque um
objeto do tipo `bytes` não pode ser alterado diretamente.

## Posição do registro

O registro usado no teste está no slot 0 da página 2. A página 2 começa em:

```text
2 * 4096 = 8192
```

Depois são pulados os 16 bytes do cabeçalho:

```text
8192 + 16 = 8208
```

Então o registro começa no byte **8208** e ocupa 8 bytes.
