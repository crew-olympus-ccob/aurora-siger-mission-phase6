"""
===============================================================================
 SCIC - SISTEMA DE COMUNICAÇÃO INTERPLANETÁRIA DA COLÔNIA
 Aurora Siger | FIAP - Ciência da Computação - Fase 6
 Grupo: Gabriel, Lucas, Matheus, Miguel e Pedro
 Colônia Aurora Siger - Base Harmonia-7, Marte | Setor 07 - Comunicação
-------------------------------------------------------------------------------
 Arquivo principal do sistema.

 CONTEXTO E CONTINUIDADE DA MISSÃO:
   Fase 4 - SIGIC: gerenciamento da infraestrutura da colônia.
   Fase 5 - NCAS:  núcleo cognitivo, com registros em texto/JSON, regras
                   booleanas e prompts estruturados. O NCAS encerrou com o
                   módulo COM (Comunicação) em estado de ALERTA - "perda
                   intermitente de sinal no link com a Terra" - e o módulo
                   AGR em MANUTENÇÃO.
   Fase 6 - SCIC (este sistema): assume exatamente esse alerta em aberto e
                   investiga o enlace de comunicação com análise numérica,
                   modelo preditivo e estruturas de dados.

   Os módulos, nomes, níveis de prioridade e consumo em kW são os mesmos
   cadastrados no dados_colonia.json da Fase 5, acrescidos dos quatro módulos
   novos que esta fase passou a monitorar (COM-R, DAT, BKP e EXT).

 O SCIC organiza os dados operacionais e de comunicação da colônia, avalia a
 confiabilidade das previsões de latência, prioriza alertas críticos com uma
 fila de prioridade (heap), permite consultas rapidas por prefixo (trie) e
 gera um painel de análise final de apoio à decisão.

 EXECUÇÃO
   Modo interativo (menu):   python codigo_fonte.py
   Modo demonstração:        python codigo_fonte.py --demo
       (executa todas as funcionalidades em sequência, sem digitar nada,
        e salva os gráficos na pasta graficos_ou_imagens/)

 DEPENDÊNCIAS: numpy, pandas, matplotlib, seaborn, scikit-learn
===============================================================================
"""

import os
import sys
import math
import json
import unicodedata

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # backend sem janela: permite salvar gráficos em qualquer ambiente
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Garante acentuação correta mesmo em terminais Windows (cp1252)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - ambientes antigos
    pass

# -----------------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# -----------------------------------------------------------------------------
PASTA = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(PASTA, "dados_aurora_siger.csv")
PASTA_GRAFICOS = os.path.join(PASTA, "graficos_ou_imagens")

# Limite operacional definido pela equipe de missão: acima disso o enlace
# compromete teleoperação e videochamadas com a Terra.
LIMITE_LATENCIA_MS = 95.0
# Erro relativo a partir do qual a previsão e considerada preocupante.
LIMITE_ERRO_RELATIVO = 0.15  # 15%

# Rotulos de exibicao: os valores são gravados no CSV sem acento (funcionam
# como chaves de dados, estaveis e faceis de filtrar); a acentuacao e aplicada
# somente na hora de mostrar na tela.
ROTULOS = {
    "ativo": "ativo",
    "alerta": "alerta",
    "manutencao": "manutenção",
    "habitacao": "habitação",
    "suporte_medico": "suporte médico",
    "suporte_vida": "suporte vital",
    "comunicacao": "comunicação",
    "laboratorio": "laboratório",
    "agricultura": "agricultura",
    "armazenamento": "armazenamento",
    "controle": "controle",
    "energia": "energia",
}


def rotulo(valor):
    """Devolve o texto acentuado de um valor de dado, para exibicao."""
    return ROTULOS.get(str(valor), str(valor))


sns.set_theme(style="whitegrid")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 30)


# =============================================================================
# BLOCO 0 - GERAÇÃO DA BASE SIMULADA DA AURORA SIGER
#
# A base de dados do SCIC é simulada. Em vez de esconder isso, o próprio
# sistema carrega o gerador: qualquer avaliador pode ler aqui exatamente
# como os 288 registros foram produzidos e recriá-los com a opção 11 do menu.
#
# A semente aleatória é fixa (42), então a base gerada é sempre idêntica
# à que acompanha a entrega - o resultado é totalmente reprodutível.
#
# CONTINUIDADE: os oito primeiros módulos vêm do cadastro oficial da colônia,
# usado desde a Fase 5 (dados_colonia.json do NCAS): mesmo código, mesmo nome,
# mesma prioridade e mesmo consumo em kW. Os quatro últimos são a expansão
# desta fase - enlace redundante, armazenamento de dados, backup e antena
# externa -, que o núcleo cognitivo anterior ainda não acompanhava.
# =============================================================================

# (código, nome, tipo, distância_m, sensor_hex, prioridade, consumo_kW, origem)
MODULOS_COLONIA = [
    ("HAB",   "Habitação",                "habitacao",       120, "0x1A3F", 4, 18.5, "Fase 5"),
    ("MED",   "Suporte Médico",           "suporte_medico",  150, "0x5F09", 5, 12.3, "Fase 5"),
    ("OXI",   "Produção de Oxigênio",     "suporte_vida",     95, "0x7B12", 5, 24.7, "Fase 5"),
    ("CTR",   "Centro de Controle",       "controle",         40, "0x3D11", 4, 15.1, "Fase 5"),
    ("ENE",   "Armazenamento de Energia", "energia",         110, "0x7A05", 5,  5.4, "Fase 5"),
    ("AGR",   "Agricultura",              "agricultura",     310, "0x2A10", 2, 21.0, "Fase 5"),
    ("LAB",   "Laboratório Científico",   "laboratorio",     420, "0x4E30", 2, 13.8, "Fase 5"),
    ("COM",   "Comunicação",              "comunicacao",      35, "0x3C01", 3,  9.6, "Fase 5"),
    ("COM-R", "Enlace Redundante",        "comunicacao",      90, "0x3C02", 3,  8.9, "Fase 6"),
    ("DAT",   "Armazenamento de Dados",   "armazenamento",    75, "0x6A77", 4, 11.2, "Fase 6"),
    ("BKP",   "Backup Redundante",        "armazenamento",   130, "0x6A78", 3,  7.8, "Fase 6"),
    ("EXT",   "Antena Externa Remota",    "comunicacao",     640, "0x3E40", 3,  6.5, "Fase 6"),
]

CICLOS_SIMULADOS = 24          # 24 ciclos (sóis marcianos), a partir de 03/09/2026
DATA_INICIAL = "2026-09-03"    # dia seguinte ao último registro do NCAS (Fase 5)

# Latência base de projeto por tipo de módulo (ms)
BASE_POR_TIPO = {
    "comunicacao": 38.0,
    "controle": 42.0,
    "armazenamento": 46.0,
    "energia": 50.0,
    "suporte_vida": 48.0,
    "habitacao": 58.0,
    "suporte_medico": 54.0,
    "agricultura": 66.0,
    "laboratorio": 72.0,
}

MENSAGENS_OK = [
    "Enlace estável, sem ocorrências",
    "Operação nominal do módulo",
    "Transmissão dentro do previsto",
]
MENSAGENS_MANUTENCAO = [
    "Manutenção preventiva de antena",
    "Manutenção programada do transceptor",
    "Calibração de sensor agendada",
]
MENSAGENS_ALERTA = [
    "Latência acima do limite operacional",
    "Perda intermitente de pacotes no enlace",
    "Queda de tensão no transmissor",
    "Interferência por tempestade de poeira",
    "Falha parcial de redundância do enlace",
]


def gerar_base_simulada(caminho=None, exibir=True):
    """Gera (ou recria) o arquivo dados_aurora_siger.csv.

    Processo gerador, documentado para que o resultado seja auditável:
      1. latência PREVISTA  = fórmula de projeto (tipo + distância + carga
         - potência), que é o que a equipe de missão consegue estimar;
      2. latência OBSERVADA = prevista + interferência atmosférica
         + ruído do sensor + falhas raras + degradação do módulo COM.

    A diferença entre as duas é justamente o que o SCIC analisa."""
    caminho = caminho or ARQUIVO_DADOS
    rng = np.random.default_rng(42)   # semente fixa -> base reprodutível
    registros = []
    id_registro = 1

    for ciclo in range(1, CICLOS_SIMULADOS + 1):
        # Índice de interferência atmosférica do ciclo (0 a 1).
        # Os ciclos 9 a 13 simulam uma tempestade de poeira marciana.
        if 9 <= ciclo <= 13:
            interferencia = float(rng.uniform(0.55, 0.95))
        else:
            interferencia = float(rng.uniform(0.02, 0.30))

        data = (
            pd.Timestamp(DATA_INICIAL) + pd.Timedelta(days=ciclo - 1)
        ).strftime("%Y-%m-%d")

        for cod, nome, tipo, dist, sensor, prioridade, consumo_kw, origem in MODULOS_COLONIA:
            # --- grandezas elétricas do transmissor (P = V x I) ---
            tensao = float(rng.normal(27.5, 1.1))            # barramento de ~28 V
            corrente = max(float(rng.normal(1.6 + dist / 900, 0.18)), 0.35)
            potencia = tensao * corrente

            # --- carga de processamento do módulo no ciclo (%) ---
            carga = float(np.clip(rng.normal(52 + prioridade * 3, 14), 5, 99))

            # --- latência prevista pelo modelo de projeto ---
            lat_prevista = round(float(
                BASE_POR_TIPO[tipo]
                + 0.045 * dist           # atraso de propagação/roteamento
                + 0.22 * carga           # fila de processamento
                - 1.35 * potencia / 10   # mais potência -> menos retransmissão
            ), 2)

            # --- latência observada pelo sensor ---
            lat_observada = (
                lat_prevista
                + 31.0 * interferencia       # efeito da poeira em suspensão
                + rng.normal(0, 3.2)         # ruído de medição do sensor
            )

            # DEGRADAÇÃO PROGRESSIVA DO MÓDULO COM
            # A Fase 5 encerrou com o COM em ALERTA ("perda intermitente de
            # sinal no link com a Terra") e a antena nunca foi reparada: ela
            # piora a cada ciclo. É o caso de manutenção preditiva que a
            # opção 9 do menu detecta por tendência.
            if cod == "COM":
                lat_observada += 0.95 * ciclo

            # Falha de hardware rara e não prevista (5% dos registros)
            if rng.random() < 0.05:
                lat_observada += float(rng.uniform(18, 60))
            lat_observada = round(float(max(lat_observada, 5.0)), 2)

            # --- status operacional derivado do desvio observado ---
            desvio = (lat_observada - lat_prevista) / lat_prevista
            if desvio > 0.35 or tensao < 25.8:
                status, mensagem = "alerta", str(rng.choice(MENSAGENS_ALERTA))
            elif rng.random() < 0.08:
                status, mensagem = "manutencao", str(rng.choice(MENSAGENS_MANUTENCAO))
            else:
                status, mensagem = "ativo", str(rng.choice(MENSAGENS_OK))

            registros.append({
                "id_registro": id_registro,
                "ciclo": ciclo,
                "data": data,
                "codigo_modulo": cod,
                "nome_modulo": nome,
                "tipo_modulo": tipo,
                "codigo_sensor": sensor,
                "distancia_antena_m": dist,
                "latencia_prevista_ms": lat_prevista,
                "latencia_observada_ms": lat_observada,
                "tensao_v": round(tensao, 2),
                "corrente_a": round(corrente, 3),
                "potencia_w": round(potencia, 2),
                "consumo_modulo_kw": consumo_kw,
                "carga_processamento_pct": round(carga, 1),
                "indice_interferencia": round(interferencia, 3),
                "status_operacional": status,
                "nivel_prioridade": prioridade,
                "mensagem_alerta": mensagem,
                "origem_cadastro": origem,
            })
            id_registro += 1

    base = pd.DataFrame(registros)
    base.to_csv(caminho, index=False, encoding="utf-8")   # gravação em disco

    if exibir:
        print(f"\n[base gerada] {os.path.basename(caminho)}")
        print(f"  Registros: {len(base)} | Módulos: {base['codigo_modulo'].nunique()} "
              f"| Ciclos: {base['ciclo'].nunique()}")
        print(f"  Período: {base['data'].min()} a {base['data'].max()}")
        print("  Semente fixa (42): a base gerada é sempre a mesma.")
    return base


# =============================================================================
# ESTRUTURA DE DADOS 1 - TRIE (árvore de prefixos)
# =============================================================================
def normalizar(texto):
    """Remove acentos e coloca em minúsculas, para que a trie encontre
    'comunicação' tanto digitando 'comu' quanto 'comunicação'.

    unicodedata.normalize('NFD', ...) separa a letra do seu acento; em
    seguida descartamos os caracteres da categoria 'Mn' (marcas de acento)."""
    decomposto = unicodedata.normalize("NFD", texto.lower().strip())
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


class NoTrie:
    """Nó da trie: guarda os filhos, a marcação de fim de palavra, o texto
    original da chave (com acento) e os registros associados a ela."""

    def __init__(self):
        self.filhos = {}          # caractere (sem acento) -> NoTrie
        self.fim_de_palavra = False
        self.texto_original = ""  # chave como deve ser exibida ao usuário
        self.registros = []       # informações ligadas a chave completa


class Trie:
    """Trie usada para busca por prefixo em nomes de módulos, códigos de
    sensores, comandos e palavras-chave de alertas.

    Vantagem: a busca depende apenas do tamanho do prefixo (O(p)), e não da
    quantidade total de registros armazenados, como aconteceria em uma
    varredura linear de lista."""

    def __init__(self):
        self.raiz = NoTrie()
        self.total_chaves = 0

    def inserir(self, chave, registro=None):
        """Insere uma chave na trie, descendo caractere a caractere.

        A árvore é percorrida pela versão SEM acento da chave, mas o texto
        original é guardado no nó final para ser exibido corretamente."""
        original = str(chave).strip()
        normalizada = normalizar(original)
        if not normalizada:
            return
        atual = self.raiz
        for caractere in normalizada:
            if caractere not in atual.filhos:
                atual.filhos[caractere] = NoTrie()
            atual = atual.filhos[caractere]
        if not atual.fim_de_palavra:
            self.total_chaves += 1
        atual.fim_de_palavra = True
        # mantem a primeira grafia inserida (a acentuada, vinda do cadastro)
        if not atual.texto_original:
            atual.texto_original = original.lower()
        if registro is not None:
            atual.registros.append(registro)

    def _no_do_prefixo(self, prefixo):
        """Percorre a trie até o último caractere do prefixo."""
        atual = self.raiz
        for caractere in normalizar(prefixo):
            if caractere not in atual.filhos:
                return None
            atual = atual.filhos[caractere]
        return atual

    def _coletar(self, no, prefixo_atual, resultados):
        """Percurso em profundidade a partir de um nó, coletando as palavras."""
        if no.fim_de_palavra:
            resultados.append((no.texto_original or prefixo_atual, no.registros))
        for caractere, filho in sorted(no.filhos.items()):
            self._coletar(filho, prefixo_atual + caractere, resultados)

    def buscar_por_prefixo(self, prefixo):
        """Retorna todas as chaves que começam com o prefixo informado.

        A busca ignora acentos: 'latência' e 'latência' levam ao mesmo nó."""
        no = self._no_do_prefixo(prefixo)
        if no is None:
            return []
        resultados = []
        self._coletar(no, normalizar(prefixo), resultados)
        return sorted(resultados, key=lambda par: par[0])

    def contem(self, chave):
        """Verifica se uma chave exata existe na trie."""
        no = self._no_do_prefixo(chave)
        return no is not None and no.fim_de_palavra


# =============================================================================
# ESTRUTURA DE DADOS 2 - HEAP (fila de prioridade máxima)
# =============================================================================
class FilaDePrioridadeAlertas:
    """Heap MÁXIMO implementado manualmente com lista e as operações
    heapify-up (ao inserir) e heapify-down (ao remover).

    O elemento da raiz (índice 0) e sempre o alerta de maior pontuacao de
    prioridade, o que permite responder "qual o alerta mais urgente agora?"
    em O(log n) na inserção/remoção e O(1) na consulta do topo.
    Em uma lista simples, seria necessário varrer todos os alertas (O(n))
    a cada consulta, ou manter a lista ordenada (O(n) por inserção)."""

    def __init__(self):
        self.itens = []  # cada item: (pontuacao, dicionario_do_alerta)

    def __len__(self):
        return len(self.itens)

    # ---- operações internas -------------------------------------------------
    def _heapify_up(self, indice):
        """Sobe o elemento recem-inserido até sua posição correta."""
        while indice > 0:
            pai = (indice - 1) // 2
            if self.itens[indice][0] > self.itens[pai][0]:
                self.itens[indice], self.itens[pai] = self.itens[pai], self.itens[indice]
                indice = pai
            else:
                break

    def _heapify_down(self, indice):
        """Desce o elemento da raiz até restaurar a propriedade de heap."""
        tamanho = len(self.itens)
        while True:
            esquerda = 2 * indice + 1
            direita = 2 * indice + 2
            maior = indice
            if esquerda < tamanho and self.itens[esquerda][0] > self.itens[maior][0]:
                maior = esquerda
            if direita < tamanho and self.itens[direita][0] > self.itens[maior][0]:
                maior = direita
            if maior == indice:
                break
            self.itens[indice], self.itens[maior] = self.itens[maior], self.itens[indice]
            indice = maior

    # ---- operações publicas -------------------------------------------------
    def inserir(self, pontuacao, alerta):
        """Insere um alerta e reorganiza o heap (heapify-up)."""
        self.itens.append((pontuacao, alerta))
        self._heapify_up(len(self.itens) - 1)

    def consultar_topo(self):
        """Retorna (sem remover) o alerta mais urgente."""
        return self.itens[0] if self.itens else None

    def remover_mais_urgente(self):
        """Remove e devolve o alerta de maior prioridade (heapify-down)."""
        if not self.itens:
            return None
        topo = self.itens[0]
        ultimo = self.itens.pop()
        if self.itens:
            self.itens[0] = ultimo
            self._heapify_down(0)
        return topo


def calcular_pontuacao_prioridade(registro, ciclo_atual):
    """Critério de prioridade do SCIC.

    Combina quatro fatores definidos pela equipe de operação:
      1. Criticidade cadastral do módulo (1 a 5)  -> peso 2.0
      2. Erro relativo da previsão de latência    -> peso 0.25 por ponto %
      3. Situação operacional (alerta/manutenção) -> bônus fixo
      4. Tempo desde o registro (ciclos)          -> peso 0.4 (envelhecimento)

    Quanto maior a pontuacao, mais urgente e o alerta."""
    erro_relativo_pct = abs(
        registro["latencia_observada_ms"] - registro["latencia_prevista_ms"]
    ) / registro["latencia_prevista_ms"] * 100

    bonus_status = {"alerta": 10.0, "manutencao": 3.0}.get(registro["status_operacional"], 0.0)

    # Alertas antigos não podem "sumir" da fila: envelhecimento limitado a 6 pontos.
    envelhecimento = min((ciclo_atual - registro["ciclo"]) * 0.4, 6.0)

    # Módulo cuja latência passou do limite operacional recebe reforco extra.
    bonus_limite = 5.0 if registro["latencia_observada_ms"] > LIMITE_LATENCIA_MS else 0.0

    pontuacao = (
        registro["nivel_prioridade"] * 2.0
        + erro_relativo_pct * 0.25
        + bonus_status
        + envelhecimento
        + bonus_limite
    )
    return round(float(pontuacao), 2)


# =============================================================================
# 1. CARGA E ORGANIZAÇÃO DOS DADOS (Pandas)
# =============================================================================
def carregar_dados(caminho=ARQUIVO_DADOS):
    """Lê o arquivo CSV, faz limpeza básica e calcula colunas derivadas."""
    if not os.path.exists(caminho):
        # O arquivo pode ter sido apagado ou o projeto copiado sem ele.
        # Em vez de falhar, o sistema recria a base simulada na hora.
        print(f"\n[AVISO] {os.path.basename(caminho)} não encontrado.")
        print("        Recriando a base simulada a partir do gerador interno...")
        gerar_base_simulada(caminho)

    df = pd.read_csv(caminho)

    # --- limpeza / consistência ---
    df = df.drop_duplicates(subset="id_registro")
    df = df.dropna(subset=["latencia_prevista_ms", "latencia_observada_ms"])
    df["status_operacional"] = df["status_operacional"].str.strip().str.lower()
    df["tipo_modulo"] = df["tipo_modulo"].str.strip().str.lower()

    # --- colunas derivadas: indicadores de comunicação e erros numéricos ---
    df["erro_absoluto_ms"] = (df["latencia_observada_ms"] - df["latencia_prevista_ms"]).abs()
    df["erro_relativo"] = df["erro_absoluto_ms"] / df["latencia_prevista_ms"]
    df["erro_relativo_pct"] = df["erro_relativo"] * 100
    # Potência recalculada a partir da Lei da Potência (P = V * I) para conferência
    df["potencia_calculada_w"] = df["tensao_v"] * df["corrente_a"]
    # Indicador operacional: disponibilidade do enlace no ciclo
    df["acima_do_limite"] = df["latencia_observada_ms"] > LIMITE_LATENCIA_MS

    return df


def visao_geral(df):
    """Mostra a visão geral da base carregada (análise exploratória)."""
    cabecalho("1. DADOS OPERACIONAIS E DE COMUNICAÇÃO DA AURORA SIGER")

    print(f"Arquivo ......... dados_aurora_siger.csv")
    print(f"Registros ....... {len(df)}")
    print(f"Módulos ......... {df['codigo_modulo'].nunique()}")
    print(f"Ciclos (sois) ... {df['ciclo'].min()} a {df['ciclo'].max()}")
    print(f"Colunas ......... {len(df.columns)}")

    print("\n--- Primeiros registros ---")
    colunas = [
        "ciclo", "codigo_modulo", "tipo_modulo", "codigo_sensor",
        "latencia_prevista_ms", "latencia_observada_ms", "status_operacional",
    ]
    print(df[colunas].head(8).to_string(index=False))

    print("\n--- Estatísticas descritivas das principais variáveis ---")
    print(
        df[["latencia_prevista_ms", "latencia_observada_ms", "tensao_v",
            "corrente_a", "potencia_w"]].describe().round(2).to_string()
    )

    print("\n--- Distribuição do status operacional ---")
    contagem = df["status_operacional"].value_counts()
    for status, qtd in contagem.items():
        print(f"  {rotulo(status):<13} {qtd:>4} registros  ({qtd / len(df) * 100:5.1f}%)")

    print("\n--- Latência média observada por tipo de módulo ---")
    resumo = (
        df.groupby("tipo_modulo")
        .agg(
            lat_prevista=("latencia_prevista_ms", "mean"),
            lat_observada=("latencia_observada_ms", "mean"),
            erro_rel_pct=("erro_relativo_pct", "mean"),
            registros=("id_registro", "count"),
        )
        .round(2)
        .sort_values("lat_observada", ascending=False)
    )
    resumo.index = [rotulo(indice) for indice in resumo.index]  # acentua para exibir
    print(resumo.to_string())


# =============================================================================
# 2. CONSULTA DE REGISTROS
# =============================================================================
def consultar_registros(df, filtro_automatico=None):
    """Consulta registros por módulo, tipo ou status operacional."""
    cabecalho("2. CONSULTA DE REGISTROS OPERACIONAIS")

    if filtro_automatico is None:
        print("Filtrar por:")
        print("  [1] Código do módulo (ex.: COM, MED, LAB)")
        print("  [2] Tipo do módulo   (ex.: comunicação)")
        print("  [3] Status           (ativo / alerta / manutenção)")
        print("  [4] Latência acima do limite operacional")
        opcao = entrada("\nOpção: ")
        valor = ""
        if opcao in ("1", "2", "3"):
            valor = entrada("Valor a pesquisar: ")
    else:
        opcao, valor = filtro_automatico
        print(f"(modo demonstração) Filtro aplicado: opção={opcao}, valor='{valor}'")

    if opcao == "1":
        resultado = df[df["codigo_modulo"].str.upper() == valor.upper()]
    elif opcao == "2":
        resultado = df[df["tipo_modulo"] == valor.lower()]
    elif opcao == "3":
        resultado = df[df["status_operacional"] == valor.lower()]
    elif opcao == "4":
        resultado = df[df["acima_do_limite"]]
    else:
        print("\n[AVISO] Opção inválida. Nenhum filtro aplicado.")
        return

    if resultado.empty:
        print("\nNenhum registro encontrado para esse filtro.")
        return

    colunas = [
        "ciclo", "codigo_modulo", "nome_modulo", "latencia_prevista_ms",
        "latencia_observada_ms", "erro_relativo_pct", "status_operacional",
    ]
    print(f"\n{len(resultado)} registro(s) encontrado(s). Exibindo até 15:\n")
    print(resultado[colunas].head(15).round(2).to_string(index=False))

    print(f"\nLatência observada média ..... {resultado['latencia_observada_ms'].mean():.2f} ms")
    print(f"Erro relativo médio .......... {resultado['erro_relativo_pct'].mean():.2f}%")
    print(f"Registros acima do limite .... {int(resultado['acima_do_limite'].sum())}")


# =============================================================================
# 3. INDICADORES E ANÁLISE DE ERROS NUMÉRICOS
# =============================================================================
def analisar_erros(df):
    """Calcula indicadores de comunicação e analisa erro absoluto/relativo,
    incluindo a discussão sobre representação em ponto flutuante."""
    cabecalho("3. INDICADORES E ANÁLISE DE ERROS NUMÉRICOS")

    # --- indicadores operacionais da colônia ---
    disponibilidade = (1 - df["acima_do_limite"].mean()) * 100
    print("--- Indicadores de comunicação da colônia ---")
    print(f"Latência média observada ............ {df['latencia_observada_ms'].mean():8.2f} ms")
    print(f"Latência máxima observada ........... {df['latencia_observada_ms'].max():8.2f} ms")
    print(f"Disponibilidade do enlace ........... {disponibilidade:8.2f}% "
          f"(ciclos abaixo de {LIMITE_LATENCIA_MS:.0f} ms)")
    print(f"Potência média de transmissão ....... {df['potencia_w'].mean():8.2f} W")
    print(f"Módulos em alerta ................... "
          f"{int((df['status_operacional'] == 'alerta').sum()):8d} registros")

    # --- erro absoluto e erro relativo ---
    print("\n--- Erro entre latência prevista e observada ---")
    print(f"Erro absoluto médio ................. {df['erro_absoluto_ms'].mean():8.2f} ms")
    print(f"Erro absoluto máximo ................ {df['erro_absoluto_ms'].max():8.2f} ms")
    print(f"Erro relativo médio ................. {df['erro_relativo_pct'].mean():8.2f}%")
    print(f"Erro relativo máximo ................ {df['erro_relativo_pct'].max():8.2f}%")

    aceitaveis = (df["erro_relativo"] <= LIMITE_ERRO_RELATIVO).mean() * 100
    print(f"Previsões com erro aceitável (<={LIMITE_ERRO_RELATIVO*100:.0f}%) . {aceitaveis:8.2f}%")

    print("\n--- Por que usar erro RELATIVO além do erro ABSOLUTO ---")
    print("Módulos com escalas diferentes de latência não podem ser comparados")
    print("apenas pelo erro absoluto. Exemplo real da base:")
    exemplo = (
        df.groupby("codigo_modulo")
        .agg(
            lat_media=("latencia_prevista_ms", "mean"),
            erro_abs=("erro_absoluto_ms", "mean"),
            erro_rel=("erro_relativo_pct", "mean"),
        )
        .round(2)
        .sort_values("erro_abs", ascending=False)
    )
    print(exemplo.head(5).to_string())
    print("\nObserve que um módulo de latência alta pode ter erro absoluto maior")
    print("e, ainda assim, erro relativo menor: proporcionalmente ele erra menos.")

    # --- piores módulos por erro relativo ---
    print("\n--- Módulos com maior erro relativo médio (previsão menos confiável) ---")
    print(exemplo.sort_values("erro_rel", ascending=False).head(5).to_string())

    # --- ponto flutuante e precisão numérica ---
    print("\n--- Ponto flutuante e precisão numérica ---")
    print("Os valores de latência são armazenados em ponto flutuante (float64).")
    print("Isso gera pequenas diferenças de arredondamento que NÃO devem ser")
    print("confundidas com falha de comunicação. Demonstração clássica:")
    print(f"  0.1 + 0.2            = {0.1 + 0.2!r}")
    print(f"  (0.1 + 0.2) == 0.3   -> {0.1 + 0.2 == 0.3}")
    print(f"  math.isclose(...)    -> {math.isclose(0.1 + 0.2, 0.3)}")

    soma_direta = df["erro_absoluto_ms"].sum()
    soma_acumulada = 0.0
    for valor in df["erro_absoluto_ms"]:
        soma_acumulada += float(valor)
    print(f"\n  Soma vetorizada dos erros  = {soma_direta!r}")
    print(f"  Soma acumulada em laço     = {soma_acumulada!r}")
    print(f"  Diferença absoluta         = {abs(soma_direta - soma_acumulada):.3e} ms")
    print("  Conclusão: a diferença é da ordem de 1e-12 ms, ou seja, milhões de")
    print("  vezes menor que o ruído do sensor (~3 ms). E ruído numérico, não")
    print("  anomalia operacional. Por isso o SCIC compara latências com")
    print("  tolerância (math.isclose) e não com igualdade exata.")

    print("\n--- Quando um erro é aceitável ou preocupante na Aurora Siger ---")
    print(f"  Erro relativo <= {LIMITE_ERRO_RELATIVO*100:.0f}% ....... aceitável: cabe na margem de projeto.")
    print(f"  Erro relativo  > {LIMITE_ERRO_RELATIVO*100:.0f}% ....... preocupante: revisar enlace/antena.")
    print(f"  Latência > {LIMITE_LATENCIA_MS:.0f} ms ........... crítico: teleoperação e suporte")
    print("                                médico remoto ficam comprometidos.")


# =============================================================================
# 4. SIMULAÇÃO NUMÉRICA (MÉTODO DE EULER)
# =============================================================================
def simular_evolucao_latencia(df, codigo_modulo=None):
    """Simula a evolução da latência de um módulo ao longo dos próximos ciclos
    usando o MÉTODO DE EULER sobre um modelo simples de recuperação do enlace:

        dL/dt = -k * (L - L_equilibrio) + perturbação

    Interpretação: após uma interferência, o enlace tende a voltar ao valor de
    equilíbrio de forma gradual, com velocidade dada pela constante k."""
    cabecalho("4. SIMULAÇÃO DA EVOLUÇÃO DA LATÊNCIA (MÉTODO DE EULER)")

    if codigo_modulo is None:
        modulos = sorted(df["codigo_modulo"].unique())
        print("Módulos disponíveis:", ", ".join(modulos))
        codigo_modulo = entrada("\nCódigo do módulo a simular (ENTER = COM): ") or "COM"
    else:
        print(f"(modo demonstração) Módulo simulado: {codigo_modulo}")

    dados_modulo = df[df["codigo_modulo"].str.upper() == codigo_modulo.upper()]
    if dados_modulo.empty:
        print(f"\n[AVISO] Módulo '{codigo_modulo}' não encontrado.")
        return None

    nome = dados_modulo["nome_modulo"].iloc[0]
    latencia_inicial = float(dados_modulo["latencia_observada_ms"].iloc[-1])
    latencia_equilibrio = float(dados_modulo["latencia_prevista_ms"].mean())

    k = 0.35      # constante de recuperação do enlace (por ciclo)
    h = 0.5       # passo de integração (meio ciclo)
    n_passos = 20

    print(f"\nMódulo ............... {codigo_modulo} - {nome}")
    print(f"Latência inicial ..... {latencia_inicial:.2f} ms (último ciclo registrado)")
    print(f"Latência de equilíbrio {latencia_equilibrio:.2f} ms (média prevista)")
    print(f"Modelo ............... dL/dt = -{k} * (L - {latencia_equilibrio:.2f})")
    print(f"Passo de Euler (h) ... {h} ciclo\n")

    tempo = 0.0
    latencia = latencia_inicial
    historico = [(tempo, latencia)]

    print(f"{'ciclo':>7} | {'latência (ms)':>14} | {'variação dL/dt':>15}")
    print("-" * 42)
    for passo in range(n_passos):
        derivada = -k * (latencia - latencia_equilibrio)   # dL/dt
        if passo % 4 == 0:
            print(f"{tempo:7.1f} | {latencia:14.2f} | {derivada:15.3f}")
        latencia = latencia + h * derivada                  # passo de Euler
        tempo = tempo + h
        historico.append((tempo, latencia))
    print(f"{tempo:7.1f} | {latencia:14.2f} | {'-':>15}")

    ciclos_ate_normalizar = None
    for t, valor in historico:
        if valor <= LIMITE_LATENCIA_MS:
            ciclos_ate_normalizar = t
            break

    print(f"\nLatência estimada ao final da simulação: {latencia:.2f} ms")
    if ciclos_ate_normalizar is not None:
        print(f"Enlace volta abaixo de {LIMITE_LATENCIA_MS:.0f} ms em ~{ciclos_ate_normalizar:.1f} ciclo(s).")
    else:
        print(f"[ATENÇÃO] O enlace NÃO volta abaixo de {LIMITE_LATENCIA_MS:.0f} ms no horizonte simulado.")
    print("\nLimitação assumida: Euler é um método de 1a ordem; o erro de")
    print("truncamento cresce com o passo h. Usamos h = 0.5 por ser suficiente")
    print("para a decisão operacional (ordem de grandeza do tempo de recuperação).")

    return historico


# =============================================================================
# 5. MODELO SIMPLES DE PREVISÃO E AVALIAÇÃO DE PERFORMANCE
# =============================================================================
def preparar_variaveis(df):
    """Monta a matriz de atributos (X) e o alvo (y) do modelo.

    Alvo:   latência observada (ms) - problema de REGRESSÃO.
    Atributos: grandezas que a colônia consegue medir ANTES da transmissão."""
    atributos_numericos = [
        "distancia_antena_m",
        "carga_processamento_pct",
        "potencia_w",
        "tensao_v",
        "indice_interferencia",
        "nivel_prioridade",
    ]
    X = df[atributos_numericos].copy()
    # Variável categórica 'tipo_modulo' transformada em colunas binárias
    X = pd.concat([X, pd.get_dummies(df["tipo_modulo"], prefix="tipo", dtype=float)], axis=1)
    y = df["latencia_observada_ms"].copy()
    return X, y


def calcular_aic_bic(y_real, y_previsto, n_parametros):
    """AIC e BIC para modelos de regressão linear (critério de comparação que
    penaliza modelos com muitos parâmetros)."""
    n = len(y_real)
    rss = float(np.sum((np.asarray(y_real) - np.asarray(y_previsto)) ** 2))
    if rss <= 0:
        return float("-inf"), float("-inf")
    aic = n * math.log(rss / n) + 2 * n_parametros
    bic = n * math.log(rss / n) + n_parametros * math.log(n)
    return aic, bic


def avaliar(nome, y_real, y_previsto):
    """Calcula e imprime MAE, MSE, RMSE e R2 de um conjunto de previsões."""
    mae = mean_absolute_error(y_real, y_previsto)
    mse = mean_squared_error(y_real, y_previsto)
    rmse = math.sqrt(mse)
    r2 = r2_score(y_real, y_previsto)
    print(f"{nome:<28} MAE={mae:7.3f}  MSE={mse:9.3f}  RMSE={rmse:7.3f}  R2={r2:7.4f}")
    return {"modelo": nome, "MAE": mae, "MSE": mse, "RMSE": rmse, "R2": r2}


def treinar_e_avaliar_modelo(df, salvar_graficos=True):
    """Treina um modelo simples de previsão de latência e avalia a performance
    com MAE, MSE, RMSE e R2, comparando com um baseline e discutindo AIC/BIC."""
    cabecalho("5. MODELO SIMPLES DE PREVISÃO E AVALIAÇÃO DE PERFORMANCE")

    X, y = preparar_variaveis(df)

    # --- divisão treino / validação / teste (60% / 20% / 20%) ---
    X_treino, X_resto, y_treino, y_resto = train_test_split(
        X, y, test_size=0.40, random_state=42
    )
    X_val, X_teste, y_val, y_teste = train_test_split(
        X_resto, y_resto, test_size=0.50, random_state=42
    )
    print(f"Divisão dos dados: treino={len(X_treino)} | validação={len(X_val)} | teste={len(X_teste)}")
    print(f"Atributos usados ({X.shape[1]}): {', '.join(X.columns)}\n")

    # --- BASELINE: prever sempre a média do treino ---
    print("--- Comparação de modelos (conjunto de VALIDAÇÃO) ---")
    baseline_val = np.full(len(y_val), y_treino.mean())
    r_baseline = avaliar("Baseline (média do treino)", y_val, baseline_val)

    # --- Modelo 1: Regressão Linear ---
    modelo_linear = LinearRegression()
    modelo_linear.fit(X_treino, y_treino)
    r_linear = avaliar("Regressão Linear", y_val, modelo_linear.predict(X_val))

    # --- Modelo 2: Ridge com Grid Search (ajuste de hiperparâmetro) ---
    grade = {"alpha": [0.01, 0.1, 1.0, 10.0, 50.0, 100.0]}
    busca = GridSearchCV(Ridge(), grade, cv=5, scoring="neg_mean_absolute_error")
    busca.fit(X_treino, y_treino)
    modelo_ridge = busca.best_estimator_
    r_ridge = avaliar(f"Ridge (alpha={busca.best_params_['alpha']})", y_val, modelo_ridge.predict(X_val))

    print(f"\nGrid Search testou {len(grade['alpha'])} valores de alpha com validação cruzada (cv=5).")
    print(f"Melhor alpha encontrado: {busca.best_params_['alpha']}")

    # --- AIC / BIC no conjunto de treino ---
    n_param = X.shape[1] + 1
    aic_lin, bic_lin = calcular_aic_bic(y_treino, modelo_linear.predict(X_treino), n_param)
    aic_rid, bic_rid = calcular_aic_bic(y_treino, modelo_ridge.predict(X_treino), n_param)
    print("\n--- Critérios de informação (quanto MENOR, melhor) ---")
    print(f"Regressão Linear   AIC={aic_lin:9.2f}   BIC={bic_lin:9.2f}")
    print(f"Ridge              AIC={aic_rid:9.2f}   BIC={bic_rid:9.2f}")
    print("AIC/BIC penalizam o número de parâmetros: como os dois modelos usam")
    print("os mesmos atributos, a diferença vem só da qualidade do ajuste.")

    # --- Escolha do modelo final pelo MAE de validação ---
    candidatos = [(r_linear["MAE"], "Regressão Linear", modelo_linear),
                  (r_ridge["MAE"], "Ridge", modelo_ridge)]
    candidatos.sort(key=lambda item: item[0])
    _, nome_final, modelo_final = candidatos[0]
    print(f"\nModelo escolhido pela validação: {nome_final}")

    # --- Avaliação FINAL no conjunto de teste (dados nunca vistos) ---
    print("\n--- Avaliação final (conjunto de TESTE) ---")
    y_previsto = modelo_final.predict(X_teste)
    resultado_teste = avaliar(f"{nome_final} (teste)", y_teste, y_previsto)
    baseline_teste = avaliar("Baseline (teste)", y_teste, np.full(len(y_teste), y_treino.mean()))

    # --- Interpretação das métricas ---
    mae, rmse, r2 = resultado_teste["MAE"], resultado_teste["RMSE"], resultado_teste["R2"]
    media_y = float(y_teste.mean())
    print("\n--- Interpretação das métricas ---")
    print(f"MAE  = {mae:.2f} ms  -> erro típico da previsão; equivale a "
          f"{mae / media_y * 100:.1f}% da latência média ({media_y:.1f} ms).")
    print(f"MSE  = {resultado_teste['MSE']:.2f} ms^2 -> penaliza erros grandes; esta em unidade")
    print("       ao quadrado, por isso não é comparável diretamente com a latência.")
    print(f"RMSE = {rmse:.2f} ms -> volta à unidade da variável (ms) e fica sensível")
    print("       aos piores casos.")
    print(f"R2   = {r2:.4f} -> o modelo explica {r2*100:.1f}% da variacao da latência.")
    print(f"\nRelacao RMSE/MAE = {rmse / mae:.2f}. Quanto mais acima de 1, mais o erro")
    print("esta concentrado em poucos registros muito ruins (os ciclos de tempestade")
    print("de poeira e as falhas de hardware raras da base).")
    print("Por isso um número só não basta: um R2 alto convive com registros")
    print("individuais de erro grande, justamente os que geram alerta na colônia.")

    # --- Importância dos atributos (coeficientes) ---
    print("\n--- Coeficientes do modelo (influencia de cada atributo na latência) ---")
    coeficientes = pd.Series(modelo_final.coef_, index=X.columns).sort_values(
        key=abs, ascending=False
    )
    print(coeficientes.head(8).round(3).to_string())

    if salvar_graficos:
        gerar_grafico_modelo(y_teste, y_previsto, nome_final)

    return {
        "modelo": modelo_final,
        "nome": nome_final,
        "colunas": list(X.columns),
        "metricas_teste": resultado_teste,
        # baseline do TESTE: e com ele que o ganho do modelo deve ser comparado,
        # porque as duas medidas vem do mesmo conjunto de dados.
        "baseline": baseline_teste,
        "baseline_validacao": r_baseline,
    }


# =============================================================================
# 6. PRIORIZAÇÃO DE ALERTAS COM HEAP
# =============================================================================
def priorizar_alertas(df, quantidade=10, ciclo_atual=None):
    """Monta a fila de prioridade dos alertas da colônia usando o heap."""
    cabecalho("6. PRIORIZAÇÃO DE ALERTAS COM HEAP (FILA DE PRIORIDADE)")

    if ciclo_atual is None:
        ciclo_atual = int(df["ciclo"].max())

    # São considerados alertas: status 'alerta'/'manutenção' ou latência acima do limite.
    alertas = df[
        (df["status_operacional"].isin(["alerta", "manutencao"]))
        | (df["acima_do_limite"])
    ]

    print(f"Ciclo atual da missão .......... {ciclo_atual}")
    print(f"Ocorrências candidatas a alerta  {len(alertas)} de {len(df)} registros")
    print("\nCritério de prioridade:")
    print("  pontuacao = 2.0 x criticidade do módulo")
    print("            + 0.25 x erro relativo (%)")
    print("            + bônus de status (alerta=10 | manutenção=3)")
    print("            + 0.4 x ciclos desde o registro (limitado a 6)")
    print("            + 5.0 se a latência passou do limite operacional")

    # --- construção do heap (cada inserção faz heapify-up) ---
    fila = FilaDePrioridadeAlertas()
    for _, registro in alertas.iterrows():
        pontuacao = calcular_pontuacao_prioridade(registro, ciclo_atual)
        fila.inserir(
            pontuacao,
            {
                "ciclo": int(registro["ciclo"]),
                "modulo": registro["codigo_modulo"],
                "nome": registro["nome_modulo"],
                "sensor": registro["codigo_sensor"],
                "latencia": float(registro["latencia_observada_ms"]),
                "erro_rel": float(registro["erro_relativo_pct"]),
                "status": registro["status_operacional"],
                "mensagem": registro["mensagem_alerta"],
            },
        )

    print(f"\nHeap construído com {len(fila)} alertas.")
    print(f"Altura aproximada da árvore: {int(math.log2(len(fila))) + 1 if len(fila) else 0} níveis")

    topo = fila.consultar_topo()
    if topo:
        print(f"\n>>> ALERTA MAIS URGENTE (raiz do heap, consulta em O(1)):")
        print(f"    Módulo {topo[1]['modulo']} - {topo[1]['nome']} | pontuação {topo[0]}")
        print(f"    {topo[1]['mensagem']} | latência {topo[1]['latencia']:.2f} ms")

    # --- remoção sucessiva: cada remoção faz heapify-down ---
    print(f"\n--- Top {quantidade} alertas em ordem de urgência ---")
    print(f"{'#':>2} | {'pontos':>6} | {'ciclo':>5} | {'módulo':<8} | {'lat(ms)':>8} | "
          f"{'erro%':>6} | {'status':<11} | mensagem")
    print("-" * 118)
    for posicao in range(1, quantidade + 1):
        item = fila.remover_mais_urgente()
        if item is None:
            break
        pontuacao, alerta = item
        print(
            f"{posicao:>2} | {pontuacao:>6.2f} | {alerta['ciclo']:>5} | {alerta['modulo']:<8} | "
            f"{alerta['latencia']:>8.2f} | {alerta['erro_rel']:>6.1f} | "
            f"{rotulo(alerta['status']):<11} | {alerta['mensagem'][:38]}"
        )

    print(f"\nRestam {len(fila)} alertas na fila, já reorganizados pelo heapify-down.")
    print("\n--- Vantagem sobre uma lista simples ---")
    n = max(len(alertas), 1)
    print(f"  Lista simples: achar o mais urgente exige varrer os {n} alertas -> O(n).")
    print(f"  Heap:          o mais urgente esta sempre na raiz  -> O(1) para consultar")
    print(f"                 e O(log n) ~= {int(math.log2(n)) + 1} comparações para reorganizar.")
    print("  Com alertas chegando a cada ciclo, o heap mantem a ordem de atendimento")
    print("  sem reordenar toda a lista a cada nova ocorrência.")


# =============================================================================
# 7. BUSCA POR PREFIXO COM TRIE
# =============================================================================
def construir_trie(df):
    """Indexa na trie: códigos de módulo, nomes, tipos, códigos de sensor,
    palavras-chave das mensagens de alerta e comandos do sistema."""
    trie = Trie()

    for _, registro in df.drop_duplicates(subset="codigo_modulo").iterrows():
        info = {
            "tipo": "modulo",
            "codigo": registro["codigo_modulo"],
            "nome": registro["nome_modulo"],
            "sensor": registro["codigo_sensor"],
        }
        trie.inserir(registro["codigo_modulo"], info)     # ex.: "com-01"
        trie.inserir(registro["nome_modulo"], info)       # ex.: "comunicação central"
        trie.inserir(registro["codigo_sensor"], info)     # ex.: "0x3c01"

    for tipo in df["tipo_modulo"].unique():
        trie.inserir(tipo, {"tipo": "categoria", "nome": tipo})

    # Palavras-chave das mensagens de alerta (cada palavra com 4+ letras)
    for mensagem in df["mensagem_alerta"].unique():
        for palavra in str(mensagem).split():
            if len(palavra) >= 4:
                trie.inserir(palavra, {"tipo": "palavra_alerta", "mensagem": mensagem})

    # Comandos cadastrados do terminal do SCIC
    for comando in [
        "comando_status", "comando_reiniciar_enlace", "comando_diagnostico",
        "comando_controle_enlace", "controle_potencia", "controle_antena",
        "consulta_latencia",
        "backup_dados", "backup_enlace", "manutencao_preventiva",
    ]:
        trie.inserir(comando, {"tipo": "comando", "nome": comando})

    # Operadores autorizados da colônia (cadastro herdado do NCAS - Fase 5)
    for operador in ["CMDT_SILVA", "ENG_ROCHA", "MED_ALVES"]:
        trie.inserir(operador, {"tipo": "operador", "nome": operador})

    return trie


def buscar_por_prefixo(df, trie=None, prefixos_automaticos=None):
    """Executa a busca por prefixo na trie."""
    cabecalho("7. BUSCA DE REGISTROS POR PREFIXO (TRIE)")

    if trie is None:
        trie = construir_trie(df)

    print(f"Trie construída com {trie.total_chaves} chaves indexadas")
    print("(códigos de módulo, nomes, tipos, códigos de sensor, palavras-chave")
    print(" de alertas e comandos do terminal).")
    print("\nPor que a trie é adequada: a busca desce um nó por caractere do")
    print("prefixo, então o custo é O(p) - depende do tamanho do que foi digitado,")
    print("não da quantidade de registros. Uma lista simples precisaria testar")
    print(f"startswith() em todas as {trie.total_chaves} chaves a cada tecla digitada.")

    if prefixos_automaticos is None:
        print("\nDigite um prefixo (ex.: 'com', 'lat', '0x3', 'hab'). ENTER vazio para voltar.")
        while True:
            prefixo = entrada("\nPrefixo > ")
            if not prefixo:
                break
            _exibir_resultados_trie(trie, prefixo)
    else:
        for prefixo in prefixos_automaticos:
            print(f"\n(modo demonstração) Prefixo pesquisado: '{prefixo}'")
            _exibir_resultados_trie(trie, prefixo)

    return trie


def _exibir_resultados_trie(trie, prefixo):
    """Formata e imprime o resultado de uma busca por prefixo."""
    resultados = trie.buscar_por_prefixo(prefixo)
    if not resultados:
        print(f"  Nenhuma chave encontrada com o prefixo '{prefixo}'.")
        return

    print(f"  {len(resultados)} chave(s) encontrada(s) para '{prefixo}':")
    for chave, registros in resultados[:12]:
        if registros:
            info = registros[0]
            if info.get("tipo") == "modulo":
                detalhe = f"módulo {info['codigo']} | sensor {info['sensor']}"
            elif info.get("tipo") == "comando":
                detalhe = "comando do terminal"
            elif info.get("tipo") == "categoria":
                detalhe = "tipo de módulo"
            elif info.get("tipo") == "operador":
                detalhe = "operador autorizado (cadastro da Fase 5)"
            else:
                detalhe = f"alerta: {info.get('mensagem', '')[:40]}"
        else:
            detalhe = ""
        print(f"    - {chave:<32} {detalhe}")
    if len(resultados) > 12:
        print(f"    ... e mais {len(resultados) - 12} resultado(s).")


# =============================================================================
# 8. DISPOSITIVOS, BASES NUMÉRICAS E ELETRICIDADE BÁSICA
# =============================================================================
def dispositivos_bases_eletricidade(df):
    """Relaciona o SCIC com arquitetura de computadores: dispositivos de
    entrada/saída, conversão entre bases numéricas e eletricidade aplicada."""
    cabecalho("8. DISPOSITIVOS, BASES NUMÉRICAS E ELETRICIDADE APLICADA")

    # --- dispositivos de entrada e saída ---
    print("--- Dispositivos de ENTRADA (alimentam o SCIC) ---")
    print("  * Sensores de latência do transceptor de cada módulo (simulados)")
    print("  * Medidores de tensão e corrente do barramento de 28 V")
    print("  * Sensor de interferência atmosférica (índice de poeira em suspensão)")
    print("  * Terminal de teclado do operador (cadastro manual de ocorrências)")
    print("\n--- Dispositivos de SAÍDA (exibem os resultados) ---")
    print("  * Terminal de texto da sala de controle (este menu)")
    print("  * Gráficos salvos em graficos_ou_imagens/ para o painel da missão")
    print("  * Relatório técnico (relatorio_tecnico.md) para a equipe de decisão")
    print("\n--- Interfaces de comunicação (nível conceitual) ---")
    print("  * Rede interna da colônia (Ethernet/Wi-Fi) ligando módulos a antena")
    print("  * USB/serial na coleta local dos sensores de cada módulo")
    print("  * Bluetooth de curto alcance nos medidores portáteis de inspeção")
    print("  * Enlace de rádio de alta potência no salto Marte-Terra")

    # --- bases numéricas ---
    print("\n--- Códigos de sensor em decimal, binário e hexadecimal ---")
    print(f"{'módulo':<8} | {'hexadecimal':>12} | {'decimal':>8} | {'binário':>20}")
    print("-" * 58)
    amostra = df.drop_duplicates(subset="codigo_modulo").head(6)
    for _, registro in amostra.iterrows():
        hexadecimal = str(registro["codigo_sensor"])
        decimal = int(hexadecimal, 16)            # conversão hex -> decimal
        binario = bin(decimal)[2:].zfill(16)      # conversão decimal -> binário
        print(f"{registro['codigo_modulo']:<8} | {hexadecimal:>12} | {decimal:>8} | {binario:>20}")

    exemplo_hex = str(amostra["codigo_sensor"].iloc[0])
    exemplo_dec = int(exemplo_hex, 16)
    print(f"\nConversão detalhada do sensor {exemplo_hex}:")
    print(f"  hexadecimal -> decimal : {exemplo_hex} = {exemplo_dec}")
    print(f"  decimal -> binário     : {exemplo_dec} = {bin(exemplo_dec)[2:]}")
    print(f"  binário -> hexadecimal : {bin(exemplo_dec)[2:]} = {hex(exemplo_dec)}")
    print(f"  Cada sensor cabe em 16 bits (2 bytes), o que permite até "
          f"{2**16} endereços distintos na rede interna da colônia.")
    print("  O primeiro digito hexadecimal identifica a família do módulo")
    print("  (1=habitação, 2=agricultura, 3=comunicação e controle,")
    print("   4=laboratório, 5=suporte médico, 6=armazenamento de dados,")
    print("   7=suporte vital e energia).")

    # --- eletricidade básica aplicada a comunicação ---
    print("\n--- Eletricidade aplicada: Lei de Ohm e potência de transmissão ---")
    print("  Lei de Ohm ......... V = R x I   ->   R = V / I")
    print("  Potência ........... P = V x I")
    print(f"\n{'módulo':<8} | {'V (V)':>7} | {'I (A)':>7} | {'P = VxI (W)':>12} | {'R = V/I (Ω)':>14}")
    print("-" * 62)
    resumo_eletrico = (
        df.groupby("codigo_modulo")
        .agg(tensao=("tensao_v", "mean"), corrente=("corrente_a", "mean"))
        .head(6)
    )
    for codigo, linha in resumo_eletrico.iterrows():
        potencia = linha["tensao"] * linha["corrente"]
        resistencia = linha["tensao"] / linha["corrente"]
        print(f"{codigo:<8} | {linha['tensao']:>7.2f} | {linha['corrente']:>7.3f} | "
              f"{potencia:>12.2f} | {resistencia:>14.2f}")

    potencia_total = df.groupby("ciclo")["potencia_w"].sum().mean()
    energia_ciclo = potencia_total * 24  # aproximando um ciclo de operação em 24 h
    print(f"\nPotência média somada de todos os transmissores: {potencia_total:.2f} W")
    print(f"Consumo aproximado por ciclo (24 h): {energia_ciclo / 1000:.2f} kWh")
    print("Esse número conecta a comunicação ao orçamento de energia da colônia:")
    print("cada retransmissão evitada pelo SCIC é energia solar poupada.")

    # --- verificação numérica da coluna de potência ---
    diferenca = (df["potencia_w"] - df["potencia_calculada_w"]).abs().max()
    print(f"\nConferência P = V x I contra a coluna armazenada:")
    print(f"  Maior diferença encontrada: {diferenca:.6f} W")
    print("  A diferença vem do arredondamento em ponto flutuante do arquivo CSV,")
    print("  não de erro de medição.")


# =============================================================================
# 10. ANÁLISE FINAL + GRÁFICOS
# =============================================================================
def gerar_grafico_modelo(y_teste, y_previsto, nome_modelo):
    """Gráfico de dispersão: valores reais x valores previstos pelo modelo."""
    os.makedirs(PASTA_GRAFICOS, exist_ok=True)
    fig, eixos = plt.subplots(1, 2, figsize=(13, 5))

    eixos[0].scatter(y_teste, y_previsto, alpha=0.7, color="#C1440E", edgecolor="white")
    minimo = min(float(np.min(y_teste)), float(np.min(y_previsto)))
    maximo = max(float(np.max(y_teste)), float(np.max(y_previsto)))
    eixos[0].plot([minimo, maximo], [minimo, maximo], "--", color="#1F3864", linewidth=2)
    eixos[0].set_xlabel("Latência observada (ms)")
    eixos[0].set_ylabel("Latência prevista pelo modelo (ms)")
    eixos[0].set_title(f"{nome_modelo}: real x previsto (teste)")

    residuos = np.asarray(y_teste) - np.asarray(y_previsto)
    sns.histplot(residuos, bins=18, kde=True, ax=eixos[1], color="#C1440E")
    eixos[1].axvline(0, color="#1F3864", linestyle="--", linewidth=2)
    eixos[1].set_xlabel("Resíduo (ms)")
    eixos[1].set_ylabel("Frequência")
    eixos[1].set_title("Distribuição dos resíduos")

    fig.suptitle("SCIC - Avaliação do modelo de previsão de latência", fontsize=13)
    fig.tight_layout()
    caminho = os.path.join(PASTA_GRAFICOS, "03_avaliacao_modelo.png")
    fig.savefig(caminho, dpi=130)
    plt.close(fig)
    print(f"\n[gráfico salvo] {os.path.relpath(caminho, PASTA)}")


def gerar_graficos_analise(df):
    """Gera os gráficos de apoio a análise final."""
    os.makedirs(PASTA_GRAFICOS, exist_ok=True)

    # --- 1. latência prevista x observada por ciclo ---
    fig, eixo = plt.subplots(figsize=(11, 5))
    por_ciclo = df.groupby("ciclo")[["latencia_prevista_ms", "latencia_observada_ms"]].mean()
    eixo.plot(por_ciclo.index, por_ciclo["latencia_prevista_ms"], marker="o",
              label="Latência prevista", color="#1F3864")
    eixo.plot(por_ciclo.index, por_ciclo["latencia_observada_ms"], marker="s",
              label="Latência observada", color="#C1440E")
    eixo.axhline(LIMITE_LATENCIA_MS, color="gray", linestyle="--",
                 label=f"Limite operacional ({LIMITE_LATENCIA_MS:.0f} ms)")
    eixo.axvspan(9, 13, alpha=0.15, color="orange", label="Tempestade de poeira")
    eixo.set_xlabel("Ciclo (sol marciano)")
    eixo.set_ylabel("Latência média (ms)")
    eixo.set_title("SCIC - Latência prevista x observada por ciclo")
    eixo.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(PASTA_GRAFICOS, "01_latencia_por_ciclo.png"), dpi=130)
    plt.close(fig)

    # --- 2. erro relativo médio por módulo ---
    fig, eixo = plt.subplots(figsize=(11, 5))
    erro_modulo = (
        df.groupby("codigo_modulo")["erro_relativo_pct"].mean().sort_values(ascending=False)
    )
    cores = ["#C1440E" if valor > LIMITE_ERRO_RELATIVO * 100 else "#1F3864" for valor in erro_modulo]
    eixo.bar(erro_modulo.index, erro_modulo.values, color=cores)
    eixo.axhline(LIMITE_ERRO_RELATIVO * 100, color="gray", linestyle="--",
                 label=f"Limite aceitável ({LIMITE_ERRO_RELATIVO*100:.0f}%)")
    eixo.set_xlabel("Módulo")
    eixo.set_ylabel("Erro relativo médio (%)")
    eixo.set_title("SCIC - Confiabilidade da previsão por módulo")
    eixo.tick_params(axis="x", rotation=45)
    eixo.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(PASTA_GRAFICOS, "02_erro_por_modulo.png"), dpi=130)
    plt.close(fig)

    # --- 4. painel operacional (boxplot + status) ---
    fig, eixos = plt.subplots(1, 2, figsize=(13, 5))
    # coluna temporaria so para exibir o tipo acentuado no eixo do grafico
    df_exibicao = df.assign(tipo_exibicao=df["tipo_modulo"].map(rotulo))
    sns.boxplot(data=df_exibicao, x="tipo_exibicao", y="latencia_observada_ms",
                ax=eixos[0], hue="tipo_exibicao", legend=False, palette="Oranges")
    eixos[0].axhline(LIMITE_LATENCIA_MS, color="#1F3864", linestyle="--")
    eixos[0].set_xlabel("Tipo de módulo")
    eixos[0].set_ylabel("Latência observada (ms)")
    eixos[0].set_title("Latência por tipo de módulo")
    eixos[0].tick_params(axis="x", rotation=30)

    contagem = df.groupby(["ciclo", "status_operacional"]).size().unstack(fill_value=0)
    cores_status = {"ativo": "#2E7D32", "manutencao": "#F9A825", "alerta": "#C1440E"}
    contagem.plot(kind="bar", stacked=True, ax=eixos[1],
                  color=cores_status)
    eixos[1].set_xlabel("Ciclo")
    eixos[1].set_ylabel("Registros")
    eixos[1].set_title("Status operacional por ciclo")
    eixos[1].legend([rotulo(c) for c in contagem.columns], title="Status")

    fig.suptitle("SCIC - Painel operacional da Aurora Siger", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(PASTA_GRAFICOS, "04_painel_operacional.png"), dpi=130)
    plt.close(fig)

    # --- 5. detecção de degradação progressiva (manutenção preditiva) ---
    # Mostra o achado principal do SCIC: o erro do módulo COM cresce de forma
    # sustentada, inclusive DEPOIS do fim da tempestade de poeira.
    fig, eixo = plt.subplots(figsize=(11, 5))
    for codigo, cor, destaque in [("COM", "#C1440E", True), ("COM-R", "#1F3864", False),
                                  ("LAB", "#2E7D32", False)]:
        serie = (
            df[df["codigo_modulo"] == codigo]
            .groupby("ciclo")["erro_relativo_pct"].mean()
        )
        if serie.empty:
            continue
        eixo.plot(serie.index, serie.values, marker="o" if destaque else ".",
                  linewidth=2.5 if destaque else 1.4, color=cor, label=codigo,
                  alpha=1.0 if destaque else 0.75)
        if destaque and len(serie) >= 3:
            # reta ajustada: o coeficiente angular e a "tendência de degradação"
            coef = np.polyfit(serie.index, serie.values, 1)
            eixo.plot(serie.index, np.polyval(coef, serie.index), "--", color=cor,
                      linewidth=1.8, label=f"tendência {codigo}: {coef[0]:+.2f} %/ciclo")

    eixo.axvspan(9, 13, alpha=0.15, color="orange", label="Tempestade de poeira")
    eixo.axhline(LIMITE_ERRO_RELATIVO * 100, color="gray", linestyle=":",
                 label=f"Limite aceitável ({LIMITE_ERRO_RELATIVO*100:.0f}%)")
    eixo.set_xlabel("Ciclo (sol marciano)")
    eixo.set_ylabel("Erro relativo médio (%)")
    eixo.set_title("SCIC - Manutenção preditiva: degradação progressiva do módulo COM")
    eixo.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(PASTA_GRAFICOS, "05_degradacao_com.png"), dpi=130)
    plt.close(fig)

    print(f"[gráficos salvos em] {os.path.relpath(PASTA_GRAFICOS, PASTA)}/")


def analise_final(df, resultado_modelo=None):
    """Consolida os resultados e apresenta a análise final de apoio à decisão."""
    cabecalho("10. ANÁLISE FINAL DOS RESULTADOS")

    ciclo_atual = int(df["ciclo"].max())
    alertas = df[df["status_operacional"] == "alerta"]
    pior_modulo = df.groupby("codigo_modulo")["erro_relativo_pct"].mean().idxmax()
    pior_erro = df.groupby("codigo_modulo")["erro_relativo_pct"].mean().max()
    ciclos_criticos = (
        df.groupby("ciclo")["acima_do_limite"].mean().sort_values(ascending=False).head(3)
    )

    print("--- Situação da comunicação da Aurora Siger ---")
    print(f"  Ciclos analisados ................. {df['ciclo'].nunique()}")
    print(f"  Disponibilidade do enlace ......... {(1 - df['acima_do_limite'].mean())*100:.1f}%")
    print(f"  Latência média observada .......... {df['latencia_observada_ms'].mean():.2f} ms")
    print(f"  Registros em alerta ............... {len(alertas)} ({len(alertas)/len(df)*100:.1f}%)")
    print(f"  Erro relativo médio da previsão ... {df['erro_relativo_pct'].mean():.2f}%")
    print(f"  Módulo menos previsível ........... {pior_modulo} (erro médio {pior_erro:.1f}%)")

    print("\n--- Ciclos mais críticos (maior proporção acima do limite) ---")
    for ciclo, proporcao in ciclos_criticos.items():
        print(f"  Ciclo {int(ciclo):>2}: {proporcao*100:5.1f}% dos módulos acima de {LIMITE_LATENCIA_MS:.0f} ms")
    print("  Esses ciclos coincidem com a tempestade de poeira simulada (9 a 13),")
    print("  o que confirma que o índice de interferência explica boa parte dos alertas.")

    if resultado_modelo:
        metricas = resultado_modelo["metricas_teste"]
        print(f"\n--- Modelo de previsão ({resultado_modelo['nome']}) ---")
        print(f"  MAE  = {metricas['MAE']:.2f} ms | RMSE = {metricas['RMSE']:.2f} ms | R2 = {metricas['R2']:.4f}")
        ganho = (1 - metricas["MAE"] / resultado_modelo["baseline"]["MAE"]) * 100
        print(f"  Ganho sobre o baseline (média): {ganho:.1f}% de redução no MAE.")

    print("\n--- Recomendações operacionais geradas pelo SCIC ---")
    print("  1. Antecipar manutenção dos módulos de maior erro relativo: a previsão")
    print(f"     falha mais neles ({pior_modulo} a frente), sinal de degradação de antena.")
    print("  2. Nos ciclos de tempestade, acionar o enlace redundante (COM-R) e")
    print("     reduzir tráfego não essencial dos laboratórios.")
    print("  3. Manter os módulos de suporte médico e comunicação no topo da fila de")
    print("     prioridade: a criticidade cadastral domina a pontuacao do heap.")
    print("  4. Toda decisão automatizada do SCIC é uma SUGESTÃO: a validação final")
    print("     continua sendo da equipe humana da colônia.")

    gerar_graficos_analise(df)

    # --- exporta o resumo em JSON (saída de dados do sistema) ---
    resumo = {
        "ciclo_atual": ciclo_atual,
        "registros": int(len(df)),
        "disponibilidade_pct": round(float((1 - df["acima_do_limite"].mean()) * 100), 2),
        "latencia_media_ms": round(float(df["latencia_observada_ms"].mean()), 2),
        "erro_relativo_medio_pct": round(float(df["erro_relativo_pct"].mean()), 2),
        "registros_em_alerta": int(len(alertas)),
        "modulo_menos_previsivel": pior_modulo,
    }
    if resultado_modelo:
        resumo["modelo"] = resultado_modelo["nome"]
        resumo["metricas_teste"] = {
            chave: round(float(valor), 4)
            for chave, valor in resultado_modelo["metricas_teste"].items()
            if chave != "modelo"
        }
    caminho_json = os.path.join(PASTA, "resumo_analise.json")
    with open(caminho_json, "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, indent=2, ensure_ascii=False)
    print(f"[resumo exportado] resumo_analise.json")


# =============================================================================
# 9. GERENCIAMENTO INTELIGENTE DA COMUNICAÇÃO (discussão conceitual)
# =============================================================================
def gerenciamento_inteligente(df):
    """Relaciona os resultados do SCIC com sistemas inteligentes de
    gerenciamento da comunicação."""
    cabecalho("9. GERENCIAMENTO INTELIGENTE DA COMUNICAÇÃO")

    alertas_por_modulo = df[df["status_operacional"] == "alerta"]["codigo_modulo"].value_counts()
    top_modulo = alertas_por_modulo.index[0] if len(alertas_por_modulo) else "-"
    top_qtd = int(alertas_por_modulo.iloc[0]) if len(alertas_por_modulo) else 0

    print("--- Sensores e coleta de dados ---")
    print(f"  Os {df['codigo_modulo'].nunique()} módulos publicam a cada ciclo latência, tensão,")
    print("  corrente e carga. Esse fluxo é o que alimenta as colunas do CSV e faz")
    print("  o papel da telemetria de uma rede IoT da colônia.")

    print("\n--- Monitoramento contínuo e detecção de anomalias ---")
    print(f"  O erro relativo funciona como detector: acima de {LIMITE_ERRO_RELATIVO*100:.0f}% o comportamento")
    print("  do módulo deixou de seguir o modelo de projeto. Na base, os ciclos 9 a 13")
    print("  acendem simultaneamente em vários módulos - assinatura de causa externa")
    print("  (tempestade), não de falha isolada de equipamento.")

    print("\n--- Automação de decisão ---")
    print("  O heap transforma dezenas de ocorrências em uma ordem de atendimento")
    print("  objetiva. A equipe não precisa ler todos os alertas: o topo da fila já")
    print("  responde 'o que atender agora'.")

    print("\n--- Redundância e armazenamento ---")
    print("  COM e COM-R formam um par redundante, assim como DAT e BKP.")
    print("  Quando o principal passa do limite, o SCIC indica o redundante como rota")
    print("  alternativa - o mesmo papel dos enlaces redundantes de uma rede real.")

    print("\n--- Manutenção preditiva ---")
    print(f"  O módulo {top_modulo} acumulou {top_qtd} registros em alerta.")
    print("\n  Detecção de TENDÊNCIA: para cada módulo, o SCIC ajusta uma reta ao")
    print("  erro relativo em função do ciclo (np.polyfit, grau 1). O coeficiente")
    print("  angular diz se o módulo está estável ou se degrada com o tempo.")
    print(f"\n  {'módulo':<8} | {'tendência (%/ciclo)':>20} | diagnóstico")
    print("  " + "-" * 62)

    tendencias = {}
    for codigo, grupo in df.groupby("codigo_modulo"):
        por_ciclo = grupo.groupby("ciclo")["erro_relativo_pct"].mean()
        if len(por_ciclo) >= 3:
            # coeficiente angular da reta ajustada: % de erro ganho por ciclo
            inclinacao = float(np.polyfit(por_ciclo.index, por_ciclo.values, 1)[0])
            tendencias[codigo] = inclinacao

    for codigo, inclinacao in sorted(tendencias.items(), key=lambda par: -par[1])[:5]:
        if inclinacao > 0.8:
            diagnostico = "DEGRADAÇÃO PROGRESSIVA - agendar manutenção"
        elif inclinacao > 0.3:
            diagnostico = "tendência de piora - monitorar"
        else:
            diagnostico = "estável"
        print(f"  {codigo:<8} | {inclinacao:>20.2f} | {diagnostico}")

    criticos = [cod for cod, inc in tendencias.items() if inc > 0.8]
    if criticos:
        print(f"\n  >>> {', '.join(criticos)} apresenta(m) erro relativo que CRESCE ciclo")
        print("      a ciclo, mesmo fora da janela de tempestade. Isso não é")
        print("      interferência ambiental (que vai e volta), é degradação de")
        print("      hardware. E o gatilho para manutenção ANTES da falha.")
        print("      O alerta do módulo COM ficou em aberto desde a Fase 5 (NCAS):")
        print("      a antena não foi reparada e a tendência confirma a piora.")

    print("\n--- Redes inteligentes e microrredes ---")
    consumo = df.groupby("ciclo")["potencia_w"].sum().mean()
    print(f"  Os transmissores consomem em média {consumo:.1f} W por ciclo. Como a colônia")
    print("  opera em microrrede solar, priorizar transmissões é diretamente uma")
    print("  decisão de energia: a rede de comunicação e a rede elétrica compartilham")
    print("  o mesmo orçamento de recursos.")


# =============================================================================
# INTERFACE DE TERMINAL
# =============================================================================
def entrada(mensagem, padrao=""):
    """Leitura segura do teclado.

    Se a entrada for encerrada (Ctrl+D, Ctrl+C ou execução com entrada
    redirecionada), devolve um valor padrão em vez de quebrar o programa."""
    try:
        return input(mensagem).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[entrada encerrada]")
        return padrao


def limpar_terminal():
    """Limpa a tela do terminal antes de voltar ao menu.

    Usa o comando nativo do sistema: 'cls' no Windows, 'clear' no Linux e
    macOS. Quando a saída está redirecionada para um arquivo (sem terminal
    de verdade), a limpeza é ignorada, para não encher o arquivo de códigos
    de controle."""
    if not sys.stdout.isatty():
        return
    os.system("cls" if os.name == "nt" else "clear")


def cabecalho(titulo):
    """Imprime um cabeçalho padronizado de seção."""
    print("\n" + "=" * 78)
    print(f" {titulo}")
    print("=" * 78)


def banner():
    print("\n" + "=" * 78)
    print(" SCIC - SISTEMA DE COMUNICAÇÃO INTERPLANETÁRIA DA COLÔNIA".center(78))
    print(" Aurora Siger - Base Harmonia-7, Marte | FIAP - Fase 6".center(78))
    print("=" * 78)


def menu_principal():
    print("\n" + "-" * 78)
    print(" MENU PRINCIPAL")
    print("-" * 78)
    print("  1 - Carregar dados e visão geral da colônia")
    print("  2 - Consultar registros operacionais")
    print("  3 - Calcular indicadores e erros numéricos")
    print("  4 - Simular evolução da latência (método de Euler)")
    print("  5 - Treinar modelo de previsão e avaliar (MAE/MSE/RMSE/R2)")
    print("  6 - Priorizar alertas críticos (heap)")
    print("  7 - Buscar registros por prefixo (trie)")
    print("  8 - Dispositivos, bases numéricas e eletricidade")
    print("  9 - Gerenciamento inteligente da comunicação")
    print(" 10 - Análise final dos resultados e gráficos")
    print(" 11 - Recriar a base simulada (mostra como os dados foram gerados)")
    print("  0 - Sair")
    print("-" * 78)


def executar_demonstracao():
    """Modo --demo: executa todas as funcionalidades em sequência."""
    banner()
    print("\n>>> MODO DEMONSTRAÇÃO: executando todas as funcionalidades do SCIC.\n")

    df = carregar_dados()
    if df is None:
        return

    visao_geral(df)
    consultar_registros(df, filtro_automatico=("3", "alerta"))
    analisar_erros(df)
    simular_evolucao_latencia(df, codigo_modulo="COM")
    resultado = treinar_e_avaliar_modelo(df)
    priorizar_alertas(df, quantidade=10)
    buscar_por_prefixo(df, prefixos_automaticos=["com", "lat", "0x3", "hab", "manut"])
    dispositivos_bases_eletricidade(df)
    gerenciamento_inteligente(df)
    analise_final(df, resultado)

    cabecalho("DEMONSTRAÇÃO CONCLUÍDA")
    print("Todas as funcionalidades do SCIC foram executadas com sucesso.")
    print("Gráficos disponíveis na pasta graficos_ou_imagens/.\n")


def main():
    """Laço principal do menu interativo."""
    if "--demo" in sys.argv:
        executar_demonstracao()
        return

    limpar_terminal()
    banner()
    df = carregar_dados()
    if df is None:
        return
    print(f"\n[OK] Base carregada: {len(df)} registros de {df['codigo_modulo'].nunique()} módulos.")

    trie = None
    resultado_modelo = None

    while True:
        menu_principal()
        opcao = entrada("Escolha uma opção: ", padrao="0")

        if opcao == "1":
            df = carregar_dados()
            if df is not None:
                visao_geral(df)
        elif opcao == "2":
            consultar_registros(df)
        elif opcao == "3":
            analisar_erros(df)
        elif opcao == "4":
            simular_evolucao_latencia(df)
        elif opcao == "5":
            resultado_modelo = treinar_e_avaliar_modelo(df)
        elif opcao == "6":
            priorizar_alertas(df)
        elif opcao == "7":
            trie = buscar_por_prefixo(df, trie)
        elif opcao == "8":
            dispositivos_bases_eletricidade(df)
        elif opcao == "9":
            gerenciamento_inteligente(df)
        elif opcao == "10":
            analise_final(df, resultado_modelo)
        elif opcao == "11":
            cabecalho("11. RECRIAR A BASE SIMULADA DA AURORA SIGER")
            print("A base é simulada e gerada pela função gerar_base_simulada(),")
            print("definida no BLOCO 0 deste mesmo arquivo. A semente aleatória é")
            print("fixa (42), portanto o arquivo recriado é idêntico ao da entrega.")
            df = gerar_base_simulada()
            df = carregar_dados()
            print("\n[OK] Base recriada e recarregada na memória.")
        elif opcao == "0":
            print("\nEncerrando o SCIC. Boa missão, Aurora Siger.\n")
            break
        else:
            print("\n[AVISO] Opção inválida. Escolha um número do menu.")

        # Pausa para o operador ler o resultado e limpa a tela em seguida,
        # para que cada seção comece com o terminal limpo.
        entrada("\nPressione ENTER para voltar ao menu...")
        limpar_terminal()
        banner()


if __name__ == "__main__":
    main()
