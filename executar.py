from minidb import Arquivo, Pagina, calcula_offset


ARQUIVO = "dados.db"


def main():
    arquivo = Arquivo(ARQUIVO)
    while arquivo.quantidade_paginas < 3:
        arquivo.aloca()

    pagina = Pagina(arquivo.le_pagina(2), numero_pagina=2)
    pagina.grava_registro(0, 1, 20260001)
    arquivo.escreve_pagina(2, pagina.como_bytes())
    arquivo.sync()

    # Cria outro objeto para provar que os dados vieram do arquivo.
    recuperado = Arquivo(ARQUIVO)
    pagina = Pagina(recuperado.le_pagina(2), numero_pagina=2)
    id_aluno, matricula = pagina.le_registro(0)

    print("Registro:", id_aluno, matricula)
    print("RID: (2, 0)")
    print("Byte inicial:", calcula_offset(2, 0))

    antes = recuperado.leituras
    registros = list(recuperado.varre())
    print("Páginas:", recuperado.quantidade_paginas)
    print("Leituras da varredura:", recuperado.leituras - antes)
    print("Registros:", len(registros))


if __name__ == "__main__":
    main()
