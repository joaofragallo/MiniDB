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
ficam reservados para o cabeçalho e depois começam os slots dos registros.

Para descobrir a posição de um registro no arquivo foi usada esta conta:

```text
pagina * 4096 + 16 + slot * 8
```

Por exemplo, para o RID `(2, 0)`:

```text
2 * 4096 + 16 + 0 * 8 = 8208
```

## Arquivos principais

- `minidb.py`: leitura e escrita de páginas e a classe `Pagina`;
- `executar.py`: grava e recupera o registro pedido no exercício;
- `tests/test_m1.py`: testes do módulo.

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
```

Para rodar os testes:

```bash
python3 -m unittest discover -s tests -v
```
