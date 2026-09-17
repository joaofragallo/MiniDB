from minidb import Pagina, calcula_offset, escreve_pagina, le_pagina


ARQUIVO = "dados.db"


# Cria a página em memória e coloca o registro no primeiro slot.
pagina = Pagina()
pagina.grava_registro(slot=0, id_aluno=1, matricula=20260001)

# A página 2 é escrita inteira. O arquivo é fechado no fim da função.
escreve_pagina(ARQUIVO, 2, pagina.como_bytes())

# Lê de novo do arquivo e transforma os bytes nos dois números originais.
pagina_recuperada = Pagina(le_pagina(ARQUIVO, 2))
id_aluno, matricula = pagina_recuperada.le_registro(0)

print("Registro recuperado:")
print("id:", id_aluno)
print("matricula:", matricula)
print("RID: (2, 0)")
print("Byte inicial:", calcula_offset(2, 0))
