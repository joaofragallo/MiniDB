from minidb import Arquivo, Pagina, calcula_offset


ARQUIVO = "dados.db"
arquivo = Arquivo(ARQUIVO)
while arquivo.quantidade_paginas < 3:
    arquivo.aloca()


# Cria a página em memória e coloca o registro no primeiro slot.
pagina = Pagina(arquivo.le_pagina(2))
pagina.grava_registro(slot=0, id_aluno=1, matricula=20260001)

# A página 2 é escrita inteira. O arquivo é fechado no fim da função.
arquivo.escreve_pagina(2, pagina.como_bytes())
arquivo.sync()

# Lê de novo do arquivo e transforma os bytes nos dois números originais.
recuperado = Arquivo(ARQUIVO)
pagina_recuperada = Pagina(recuperado.le_pagina(2))
id_aluno, matricula = pagina_recuperada.le_registro(0)

print("Registro recuperado:")
print("id:", id_aluno)
print("matricula:", matricula)
print("RID: (2, 0)")
print("Byte inicial:", calcula_offset(2, 0))
antes = recuperado.leituras
registros = list(recuperado.varre())
print("Páginas no arquivo:", recuperado.quantidade_paginas)
print("Leituras da varredura:", recuperado.leituras - antes)
print("Registros encontrados:", len(registros))
