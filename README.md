# Aurora Siger | SCIC: Sistema de Comunicação Interplanetária da Colônia (Fase 6)

**FIAP | Ciência da Computação | Grupo:** Gabriel, Lucas, Matheus, Miguel e Pedro

---

## Descrição

Sistema computacional desenvolvido para organizar e analisar os dados de comunicação da colônia Aurora Siger em Marte. Cada módulo da base reporta, a cada ciclo, a latência medida pelo sensor do transceptor, as grandezas elétricas do transmissor e o nível de interferência atmosférica. O SCIC compara a latência observada com a prevista pelo modelo de projeto, avalia a confiabilidade dessa previsão, ordena os alertas críticos, permite consultas por prefixo e gera um painel de apoio à decisão, tudo pelo terminal.

O sistema dá continuidade ao SIGIC (Fase 4) e ao NCAS (Fase 5). O núcleo cognitivo da fase anterior encerrou com o módulo COM em ALERTA, com a mensagem "perda intermitente de sinal no link com a Terra", registrada em 01/09/2026. A base do SCIC começa em 03/09/2026 e investiga exatamente esse alerta. Ele nunca foi resolvido: o sistema detecta que a antena se degrada **+1,58 pontos percentuais de erro por ciclo**.

---

## Funcionalidades

| Bloco | Função |
|---|---|
| Geração da base | Simulação reprodutível de 288 registros (semente fixa 42), embutida no próprio código |
| Organização dos dados | Leitura, limpeza e análise exploratória com Pandas; colunas derivadas de erro |
| Análise numérica | Erro absoluto, erro relativo e efeitos de ponto flutuante (`math.isclose`) |
| Método de Euler | Simulação da recuperação do enlace: `dL/dt = −k(L − L_equilíbrio)` |
| Modelo preditivo | Ridge e Regressão Linear com treino/validação/teste, Grid Search, AIC e BIC |
| Métricas | MAE, MSE, RMSE e R², com interpretação da relação RMSE/MAE |
| Heap | Fila de prioridade máxima implementada à mão, com heapify-up e heapify-down |
| Trie | Busca por prefixo em 88 chaves, com normalização de acentos |
| Arquitetura | Dispositivos de E/S, conversão hex/decimal/binário, Lei de Ohm e potência |
| Manutenção preditiva | Detecção de tendência de degradação por ajuste de reta (`np.polyfit`) |

---

## Como executar

```bash
pip install numpy pandas matplotlib seaborn scikit-learn

python codigo_fonte.py          # menu interativo
python codigo_fonte.py --demo   # executa tudo em sequência, sem digitar nada
```

O modo `--demo` percorre as onze opções na ordem, gera os cinco gráficos em `graficos_ou_imagens/` e exporta o `resumo_analise.json`. É o modo usado na gravação do vídeo.

**Dependências:** NumPy, Pandas, Matplotlib, Seaborn e scikit-learn, todas trabalhadas na fase. Os módulos `os`, `sys`, `math`, `json` e `unicodedata` são da biblioteca padrão e não precisam ser instalados (`unicodedata` faz a busca sem acento da trie). Python 3.9 ou superior.

Se o arquivo `dados_aurora_siger.csv` for apagado, o sistema recria a base automaticamente na próxima execução, em vez de falhar. A opção 11 do menu faz o mesmo sob demanda.

---

## Módulos da colônia

| ID | Nome | Tipo | Consumo (kW) | Prioridade | Sensor | Origem |
|---|---|---|---|---|---|---|
| HAB | Habitação | habitação | 18.5 | 4/5 | 0x1A3F | Fase 5 |
| MED | Suporte Médico | suporte médico | 12.3 | 5/5 | 0x5F09 | Fase 5 |
| OXI | Produção de Oxigênio | suporte vital | 24.7 | 5/5 | 0x7B12 | Fase 5 |
| CTR | Centro de Controle | controle | 15.1 | 4/5 | 0x3D11 | Fase 5 |
| ENE | Armazenamento de Energia | energia | 5.4 | 5/5 | 0x7A05 | Fase 5 |
| AGR | Agricultura | agricultura | 21.0 | 2/5 | 0x2A10 | Fase 5 |
| LAB | Laboratório Científico | laboratório | 13.8 | 2/5 | 0x4E30 | Fase 5 |
| COM | Comunicação | comunicação | 9.6 | 3/5 | 0x3C01 | Fase 5 |
| COM-R | Enlace Redundante | comunicação | 8.9 | 3/5 | 0x3C02 | **Fase 6** |
| DAT | Armazenamento de Dados | armazenamento | 11.2 | 4/5 | 0x6A77 | **Fase 6** |
| BKP | Backup Redundante | armazenamento | 7.8 | 3/5 | 0x6A78 | **Fase 6** |
| EXT | Antena Externa Remota | comunicação | 6.5 | 3/5 | 0x3E40 | **Fase 6** |

Os oito primeiros vêm do cadastro oficial da colônia, com código, nome, prioridade e consumo idênticos ao `dados_colonia.json` da Fase 5. Os quatro últimos são a expansão desta fase, já que o NCAS não acompanhava enlace redundante, armazenamento de dados nem antena externa.

O primeiro dígito hexadecimal do sensor identifica a família do módulo: 1 habitação, 2 agricultura, 3 comunicação e controle, 4 laboratório, 5 suporte médico, 6 armazenamento, 7 suporte vital e energia. Com isso, o prefixo do código vira uma consulta por categoria na trie.

---

## Arquivos da entrega

| Arquivo | Conteúdo |
|---|---|
| `codigo_fonte.py` | Arquivo principal e único arquivo Python: gerador da base, menu, trie e heap |
| `dados_aurora_siger.csv` | Base simulada: 288 registros, 12 módulos, 24 ciclos, 20 colunas |
| `relatorio_tecnico.md` | Relatório técnico completo, com as 5 figuras incorporadas |
| `README.md` | Este arquivo |
| `link_video.txt` | Link do vídeo de apresentação no YouTube (não listado) |
| `graficos_ou_imagens/` | Gráficos gerados pelo sistema durante a execução |

---

## Menu do sistema

```
  1 - Carregar dados e visão geral da colônia
  2 - Consultar registros operacionais
  3 - Calcular indicadores e erros numéricos
  4 - Simular evolução da latência (método de Euler)
  5 - Treinar modelo de previsão e avaliar (MAE/MSE/RMSE/R2)
  6 - Priorizar alertas críticos (heap)
  7 - Buscar registros por prefixo (trie)
  8 - Dispositivos, bases numéricas e eletricidade
  9 - Gerenciamento inteligente da comunicação
 10 - Análise final dos resultados e gráficos
 11 - Recriar a base simulada (mostra como os dados foram gerados)
  0 - Sair
```

---

## Exemplo de uso

**Heap, priorização dos alertas críticos (opção 6):**

```
--- Top 10 alertas em ordem de urgência ---
 # | pontos | ciclo | módulo   |  lat(ms) |  erro% | status      | mensagem
----------------------------------------------------------------------------
 1 |  50.49 |    18 | BKP      |   116.40 |  108.4 | alerta      | Queda de tensão no transmissor
 2 |  48.56 |    11 | HAB      |   131.65 |   81.4 | alerta      | Perda intermitente de pacotes
 3 |  42.92 |    10 | DAT      |    95.13 |   57.3 | alerta      | Queda de tensão no transmissor
 4 |  42.57 |    13 | COM      |    90.13 |   88.7 | alerta      | Latência acima do limite
 5 |  42.34 |    10 | MED      |   101.61 |   46.9 | alerta      | Perda intermitente de pacotes

  Lista simples: achar o mais urgente exige varrer os 109 alertas -> O(n).
  Heap:          o mais urgente está sempre na raiz  -> O(1) para consultar
                 e O(log n) ~= 7 comparações para reorganizar.
```

**Trie, busca por prefixo de código de sensor (opção 7):**

```
Prefixo > 0x3
  4 chave(s) encontrada(s) para '0x3':
    - 0x3c01                           módulo COM | sensor 0x3C01
    - 0x3c02                           módulo COM-R | sensor 0x3C02
    - 0x3d11                           módulo CTR | sensor 0x3D11
    - 0x3e40                           módulo EXT | sensor 0x3E40
```

**Manutenção preditiva, detecção de degradação (opção 9):**

```
  módulo   |  tendência (%/ciclo) | diagnóstico
  --------------------------------------------------------------
  COM      |                 1.58 | DEGRADAÇÃO PROGRESSIVA - agendar manutenção
  CTR      |                 0.79 | tendência de piora - monitorar
  AGR      |                 0.46 | tendência de piora - monitorar
  EXT      |                 0.01 | estável

  >>> COM apresenta erro relativo que CRESCE ciclo a ciclo, mesmo fora da
      janela de tempestade. Isso não é interferência ambiental (que vai e
      volta), é degradação de hardware.
```

---

## Modelo de previsão

O modelo estima a latência observada a partir de grandezas mensuráveis antes da transmissão: distância, carga, potência, tensão, interferência, prioridade e tipo do módulo.

| Modelo | MAE | RMSE | R² |
|---|---|---|---|
| Baseline (média) | 14,005 | 16,907 | −0,0113 |
| **Ridge (α = 1,0)** | **4,439** | **6,684** | **0,8419** |

O ganho sobre o baseline é de 68,3% no MAE. A relação RMSE/MAE de 1,51 é o dado mais informativo, porque mostra que o erro se concentra em poucos registros muito ruins: os ciclos de tempestade e, principalmente, o módulo COM, cuja degradação nenhum atributo do modelo consegue explicar. Foi preciso cruzar o modelo com a análise de tendência para chegar ao diagnóstico, e é por isso que o SCIC permanece como sistema de apoio, com a decisão final sob responsabilidade da equipe humana.

---

## Convenção de acentuação

As mensagens, os comentários e os nomes exibidos estão acentuados em português. Os valores usados como chave de dados (`tipo_modulo`, `status_operacional`) ficam sem acento no CSV, porque servem para filtrar e agrupar; a acentuação é aplicada na exibição pelo dicionário `ROTULOS`. A busca da trie ignora acentos nos dois sentidos, então `latencia` e `latência` chegam ao mesmo nó. O código chama `sys.stdout.reconfigure(encoding="utf-8")` na inicialização, o que garante a exibição correta também em terminais Windows com codificação legada.

---

## Estrutura do código

```
codigo_fonte.py
├── Bloco 0 : Geração da base simulada (MODULOS_COLONIA, gerar_base_simulada)
├── Estrutura 1: Trie (normalizar, NoTrie, Trie)
├── Estrutura 2: Heap (FilaDePrioridadeAlertas, calcular_pontuacao_prioridade)
├── 1 : Carga e organização dos dados (carregar_dados, visao_geral)
├── 2 : Consulta de registros (consultar_registros)
├── 3 : Indicadores e erros numéricos (analisar_erros)
├── 4 : Simulação de Euler (simular_evolucao_latencia)
├── 5 : Modelo e métricas (preparar_variaveis, calcular_aic_bic, avaliar,
│        treinar_e_avaliar_modelo)
├── 6 : Priorização com heap (priorizar_alertas)
├── 7 : Busca com trie (construir_trie, buscar_por_prefixo)
├── 8 : Dispositivos, bases numéricas e eletricidade
├── 9 : Gerenciamento inteligente (gerenciamento_inteligente)
├── 10: Análise final e gráficos (gerar_graficos_analise, analise_final)
└── Interface: banner, menu_principal, executar_demonstracao, main
```

---

*Aurora Siger. Exploramos dados. Construímos soluções. Geramos impacto para o amanhã em Marte.*
