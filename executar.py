from minidb import Arquivo, Cache, Pagina, calcula_offset


ARQUIVO = "dados.db"


def main():
    arquivo = Arquivo(ARQUIVO)
    while arquivo.quantidade_paginas < 3:
        arquivo.aloca()

    cache = Cache(arquivo)
    dados = cache.fixa(2)
    sujou = False
    try:
        pagina = Pagina(dados, numero_pagina=2)
        pagina.grava_registro(0, 1, 20260001)
        sujou = True
    finally:
        cache.solta(2, sujou)
    cache.descarrega()

    # Cria outro objeto para provar que os dados vieram do arquivo.
    recuperado = Arquivo(ARQUIVO)
    cache = Cache(recuperado)
    dados = cache.fixa(2)
    try:
        pagina = Pagina(dados, numero_pagina=2)
        id_aluno, matricula = pagina.le_registro(0)
    finally:
        cache.solta(2)

    print("Registro:", id_aluno, matricula)
    print("RID: (2, 0)")
    print("Byte inicial:", calcula_offset(2, 0))

    print("Páginas:", recuperado.quantidade_paginas)
    antes = recuperado.leituras
    for _ in range(2):
        list(recuperado.varre())
    print("Leituras sem cache (2 varreduras):", recuperado.leituras - antes)
    # Um cache novo permite comparar a primeira e a segunda varredura.
    cache = Cache(recuperado)
    for rodada in (1, 2):
        antes = recuperado.leituras
        registros = list(cache.varre())
        print("Leituras da varredura {}:".format(rodada), recuperado.leituras - antes)
    print("Registros:", len(registros))
    print("Acertos:", cache.acertos)
    print("Faltas:", cache.faltas)


if __name__ == "__main__":
    main()
