from diagrams import Diagram, Cluster
from diagrams.gcp.ml import VertexAI
from diagrams.programming.language import Python
from diagrams.onprem.client import Client, User
#from diagrams.generic.blank import Blank
from IPython.display import Image, display

with Diagram(
    "agent",
    show=True,
    direction="TB",
    graph_attr={
        "splines": "ortho",
        "nodesep": "1.2",
        "ranksep": "1.8",
    },
    node_attr={
        "margin": "0.3",
    },
):

    user = User("Usuário")
    client = Client("output")

    with Cluster("agent.py"):

        agent = VertexAI("Vertex AI\n(gemini2.5-flash)")


        analisar = Python("analisar_dados_arquivo.py")
        baixar = Python("baixar_arquivo_dados.py")
        buscar = Python("buscar_infos_base.py")
        graficos = Python("gerar_graficos.py")
        cache = Python("gerenciar_cache_sessao.py")
        bases = Python("listar_bases.py")
        recursos = Python("listar_recursos_base.py")

        with Cluster("Operações auxiliares"):
            Python(
                "_operacoes_básicas.py\n"
                "_operacoes_concessionárias\n"
                "_operacoes_filtros.py\n"
                "_operacoes_turnos.py\n"
                "utils.py"
            )


        agent >> [
            analisar,
            baixar,
            buscar,
            graficos,
            cache,
            bases,
            recursos,
        ]

    user >> agent >> client

display(Image(filename="agent.png", embed=True))