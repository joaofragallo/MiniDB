
# MiniDB — Banco de Dados II

### Discentes

* Joao Antonio Fragallo - 202511140010
* Erick Wilson

Projeto desenvolvido para a disciplina **Banco de Dados II**.

O objetivo é construir um pequeno sistema gerenciador de banco de dados do zero, implementando gradualmente as principais estruturas internas de um SGBD.

A ideia é entender o que acontece entre uma consulta SQL e o armazenamento dos dados em disco.

## Objetivo final

Ao final da disciplina, o MiniDB deverá ser capaz de executar comandos como:

```sql
CREATE TABLE aluno (id INT, matricula INT);
INSERT INTO aluno VALUES (1, 20260001);
SELECT * FROM aluno WHERE id = 1;
