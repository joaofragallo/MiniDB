# NOTES.md — M1, M2 e M3

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

## M2 — Cache de páginas

Escolhemos 16 frames por padrão: 16 * 4096 = 64 KiB de buffers, além das
estruturas do Python. É suficiente para exemplos pequenos e permite observar
expulsões usando uma capacidade menor nos testes.

`frames` associa o número da página ao seu `bytearray`. `Pagina` preserva essa
referência para alterar o próprio buffer do cache. `fixada` conta os usuários
de cada página, `suja` guarda as páginas alteradas e `uso` é um `OrderedDict`,
da página menos recente para a mais recente. Cada `fixa()` atualiza a ordem
LRU; `solta()` reduz o contador e pode marcar a página como suja. Se todas
estiverem fixadas, uma expulsão gera erro.

A principal decisão foi manter `Arquivo` como a camada de armazenamento do
M1 e colocar `insere()` e `varre()` também no cache. No M2, o programa usa
esses métodos do cache. A inserção procura espaço nas páginas em memória,
pois a indicação de página livre no disco pode estar atrasada. Essa busca
linear é simples e suficiente para esta etapa do projeto.

As operações liberam as páginas com `try/finally`. Uma varredura interrompida
deve ser fechada com `close()` para liberar imediatamente a página atual.
Alocação e manutenção dos metadados continuam sob responsabilidade de `Arquivo`.

Alterações ficam na RAM até a expulsão ou `descarrega()`, que grava páginas
sujas e chama `Arquivo.sync()`. Essa é a base para steal/no-force: é possível
escrever uma página antes de uma futura confirmação, e uma alteração não
obriga escrita imediata. Ainda não há transações, COMMIT, WAL, UNDO ou REDO;
um encerramento sem descarregar pode perder alterações que estejam na RAM.

### Testes e medição do M2

Os testes cobrem hit/miss, LRU (`1, 2, 3, 1, 4` expulsa a página 2),
fixações múltiplas, cache totalmente fixado, escrita de página suja na
expulsão, descarregamento, reabertura e inserção além dos 510 slots.
Também verificam liberação após erro e preservação do buffer se a escrita falhar.
A persistência após expulsão é conferida em outro processo Python, como pede
o slide. O teste de acerto confirma que o cache devolve o mesmo buffer.

Para o exemplo com duas páginas de dados, duas varreduras diretas do M1
exigem 4 leituras. Com cache de 16 frames, a primeira varredura exige 2 e
a segunda exige 0, totalizando 2 faltas e 2 acertos. `leituras` conta chamadas
de leitura de páginas de dados na camada de arquivo; não mede acessos físicos
ao dispositivo, pois o sistema operacional também pode manter um cache.


`executar.py` mede as duas varreduras sem cache e depois as duas com cache.
A entrega da disciplina também pede pull request e histórico de commits;
esses passos são separados da implementação local.

## M3 — Árvore B+

Requisitos:
Implementamos busca, inserção com divisão de folhas e nós internos, crescimento
da raiz e consulta por intervalo. Não há remoção. Chaves são IDs `uint32`
únicos; tentar inserir uma chave repetida gera `ValueError`.

`arvore_bmais.py` mantém o índice separado dos registros. O arquivo `.idx`
tem páginas de 4096 bytes, lidas e alteradas pelo `Cache` existente. Um pequeno
pager `_ArquivoIndice` cuida das páginas do índice, pois `Arquivo` valida
cabeçalhos de registros do M1. Não alteramos `minidb.py` nem o formato do M1/M2.

### Representação do nó dentro da página

Todos os números usam little-endian. A página 0 contém o cabeçalho `<8sIII>`:
assinatura `MDBIDX01` (8 bytes), quantidade de páginas (4), página raiz (4)
e máximo de chaves por nó (4). O restante fica zerado.

Cada nó tem um cabeçalho de 16 bytes (`<B3xII4x>`): indicador de folha (1 byte),
3 bytes de preenchimento, quantidade de chaves (4), próxima folha (4, zero
quando não existe) e 4 bytes de preenchimento.

- Folha: após o cabeçalho, entradas `<III>` de 12 bytes com chave, página do
  registro e slot. Cabem `(4096 - 16) // 12 = 340` entradas.
- Interno: após o cabeçalho, todas as chaves `uint32`, seguidas dos números
  das páginas dos filhos `uint32`. São N chaves e N+1 filhos. Usamos o mesmo
  limite de 340 chaves, embora os internos comportem mais.

Ao dividir uma folha, a primeira chave da metade direita é copiada para o
pai, permanecendo na folha. Ajustamos os ponteiros entre folhas. Ao dividir
um nó interno, a chave central vai para o pai e sai do nó dividido.
Uma divisão da raiz cria outra raiz. A busca usa igualdade para descer à direita
do separador. O intervalo desce uma vez e segue as próximas folhas.

`_No.de_bytes()` e `_No.como_bytes()` cuidam do formato binário, como a
classe `Pagina` do M1. A árvore concentra os algoritmos: `_insere()` insere
e `_divide()` separa um nó cheio e devolve o separador para o pai.

`_le()` libera o buffer depois de decodificar o nó, e `_grava()` fixa a página
apenas enquanto copia sua representação binária. Assim, a recursão não mantém
os ancestrais fixados e funciona até com cache de uma página.

Chame `descarrega()` nos dados e no índice antes de encerrar. O índice grava
os nós antes dos metadados da raiz. Não há recuperação de falhas nem transação
atômica entre os dois arquivos. Alterações da tabela não atualizam o índice
automaticamente; a aplicação insere o RID explicitamente.

Os testes reproduzem os dois exercícios do slide, conferem divisões em vários
níveis, folhas na mesma profundidade, separadores, busca ausente, duplicatas,
intervalos, RIDs do M1 e reabertura. Também exercitam o limite real de 340
chaves e a expulsão de páginas com cache de uma página.
