# NOTES.md — M1 e M2

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

Requisitos conferidos com a [Aula 02 — Cache de páginas](https://gustavopinto.org/assets/slides/bd2-2026/aula02.html).
`executar.py` mede as duas varreduras sem cache e depois as duas com cache.
A entrega da disciplina também pede pull request e histórico de commits;
esses passos são separados da implementação local.
