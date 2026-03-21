# Visualizacao & Geracao de Relatorios

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/reporting/`
**Proprietario:** camada de apresentacao do Macena CS2 Analyzer

## Introducao

Este pacote transforma dados brutos de analise de partida em artefatos visuais legiveis
e relatorios estruturados. Ele se situa na camada mais externa da arquitetura, consumindo
saidas das pipelines de processamento, analise e coaching para produzir heatmaps,
overlays diferenciais, anotacoes de momentos criticos e relatorios Markdown
multi-secao. Todo o rendering e suportado por Matplotlib com gerenciamento
deterministico do ciclo de vida das figuras para prevenir vazamentos de memoria.

## Inventario de Arquivos

| Arquivo | Proposito | Exports Principais |
|---------|-----------|-------------------|
| `visualizer.py` | Motor de visualizacao de mapas baseado em Matplotlib | `MatchVisualizer`, `generate_highlight_report()` |
| `report_generator.py` | Construtor de relatorios de partida multi-secao | `MatchReportGenerator` |
| `__init__.py` | Marcador de pacote | -- |

## Arquitetura & Conceitos

### Motor de Visualizacao de Mapas (`visualizer.py`)

`MatchVisualizer` e a classe central de rendering. Ela produz tres categorias de saida
visual:

1. **Heatmaps de Posicao** (`generate_heatmap`) -- histograma 2D das posicoes de
   jogadores sobreposto ao fundo do mapa. Usa uma grade de 64 bins com colourmap
   `"magma"` e limite minimo de contagem (`cmin=1`) para suprimir bins vazios.

2. **Overlays Diferenciais** (`render_differential_overlay`) -- heatmap divergente
   comparando posicionamento do usuario contra baselines profissionais. O algoritmo:
   - Converte cada conjunto de posicoes em uma grade de densidade com `resolution`
     configuravel (padrao 128).
   - Aplica desfoque Gaussiano (`sigma=5.0`) via `scipy.ndimage.gaussian_filter`.
   - Normaliza cada densidade independentemente, depois computa a diferenca.
   - Mascara regioes com atividade insignificante (limiar `< 0.02`).
   - Renderiza com colourmap divergente `RdBu_r` e `TwoSlopeNorm` centrado em zero.
   - Regioes azuis indicam posicionamento pesado do usuario; regioes vermelhas indicam
     posicionamento pesado de profissionais.

3. **Mapas de Momentos Criticos** (`render_critical_moments`) -- scatter plot anotado
   de eventos-chave identificados pelo `ChronovisorScanner`. Cada momento e renderizado
   como marcador colorido por severidade, formatado por tipo e dimensionado por escala:

   | Severidade | Cor | Tipo | Marcador | Escala | Pixels |
   |------------|-----|------|----------|--------|--------|
   | critical | vermelho | play | `^` (triangulo para cima) | macro | 350 |
   | critical | vermelho | mistake | `v` (triangulo para baixo) | standard | 200 |
   | significant | laranja | play/mistake | `^` / `v` | standard | 200 |
   | notable | ouro | play/mistake | `o` (circulo) | micro | 100 |

4. **Graficos de Erros por Round** (`plot_round_errors`) -- scatter plot marcando
   localizacoes de morte (vermelho `x`) e decisoes ruins sinalizadas pelo coach
   (laranja `P`) para um unico round.

Todos os metodos de rendering seguem o padrao **try/finally** (`DA-VZ-01`),
garantindo `plt.close(fig)` mesmo quando `savefig` lanca excecao. Isso previne
vazamentos de figuras Matplotlib em condicoes de erro.

#### Fundo do Mapa & Limites

Imagens de fundo sao carregadas de `assets/maps/` usando caminhos definidos em
`data/map_tensors.json`. Uma guarda de path traversal (`VZ-02`) valida que o caminho
de imagem resolvido permaneca dentro de `assets_dir` antes do carregamento. Seis mapas
possuem limites hardcoded em `_get_bounds()`: `de_mirage`, `de_inferno`, `de_dust2`,
`de_nuke`, `de_overpass` e `de_ancient`. Mapas desconhecidos recaem para bounding box
`(-4000, 4000, -4000, 4000)`.

### Gerador de Relatorios (`report_generator.py`)

`MatchReportGenerator` orquestra a pipeline completa de relatorios:

1. **Parse** -- carrega o arquivo demo via `DemoLoader`.
2. **Extracao** -- itera os frames parseados para coletar posicoes de jogadores e
   eventos de morte.
3. **Visualizacao** -- chama `MatchVisualizer.generate_heatmap()` para produzir a
   heatmap de posicionamento.
4. **Escrita** -- produz um arquivo de relatorio Markdown com timestamp contendo:
   - Nome do mapa e data de geracao.
   - Imagem heatmap incorporada (caminho relativo, `RG-02`).
   - Secao de analise de erros fundamentais.

O diretorio de saida e ancorado a `USER_DATA_ROOT/reports` com guarda de escape de
caminho (`RG-01`) garantindo que o relatorio permaneca sob a raiz de dados do usuario.

#### Anotacoes de Seguranca

| Codigo | Guarda |
|--------|--------|
| `DA-VZ-01` | Fechamento de figuras `try/finally` para prevenir vazamentos de memoria |
| `VZ-02` | Prevencao de path traversal para imagens de fundo de mapa |
| `DA-RG-01` | Ancoragem de caminho absoluto para diretorio de saida de relatorios |
| `RG-01` | Validacao de escape de caminho garantindo saida sob `USER_DATA_ROOT` |
| `RG-02` | Caminho relativo em Markdown para evitar exposicao da estrutura do filesystem |

### Integracao de Highlight Report (`generate_highlight_report`)

A funcao a nivel de modulo `generate_highlight_report(match_id, map_name)` conecta
o modelo RAP Coach com o motor de visualizacao. Ela:

1. Verifica se o modelo RAP esta habilitado via `get_setting("USE_RAP_MODEL")`.
2. Instancia `ChronovisorScanner` e escaneia a partida em busca de momentos criticos.
3. Converte cada `CriticalMoment` em um dict de anotacao highlight.
4. Renderiza a imagem de mapa anotada via `render_critical_moments()`.

Esta funcao e guardada por um amplo `try/except` com logging de erros, garantindo que
falhas de visualizacao nunca causem crash da pipeline chamadora.

## Integracao

| Consumidor | Uso |
|------------|-----|
| `apps/qt_app/screens/` | Rendering de graficos inline em `PerformanceScreen`, `MatchDetailScreen` |
| `backend/services/analysis_orchestrator.py` | Chama `generate_highlight_report()` durante pos-analise |
| `backend/nn/rap_coach/chronovisor_scanner.py` | Fornece objetos `CriticalMoment` para rendering |
| `ingestion/demo_loader.py` | Fornece frames parseados consumidos por `MatchReportGenerator` |
| `core/config.py` | `USER_DATA_ROOT` para ancoragem de caminho de saida de relatorios |

## Formatos de Saida

| Formato | DPI | Caso de Uso |
|---------|-----|-------------|
| PNG | 150 | Exibicao em UI, previews inline |
| PNG (alta resolucao) | 300 | Incorporacao em PDF, arquivamento |
| Markdown | -- | Relatorios de texto estruturado com referencias de imagens incorporadas |

## Notas de Desenvolvimento

- **Ciclo de vida das figuras**: cada figura Matplotlib deve ser criada e fechada no
  mesmo escopo de metodo. Nunca armazene referencias de figuras como atributos de
  instancia.
- **Saida deterministica**: nomes de arquivo incluem nome do mapa e timestamp para
  prevenir colisoes. Bins de heatmap e colourmap sao fixos para reprodutibilidade.
- **Isolamento de dependencias**: `scipy.ndimage.gaussian_filter` e a unica importacao
  do SciPy; `numpy` e usado para computacao de grade. Ambos sao dependencias
  obrigatorias.
- **Testes**: testes do visualizer usam `matplotlib.use("Agg")` para evitar requisitos
  de backend GUI. Testes do report generator fazem mock do `DemoLoader` e verificam
  a saida de arquivos.
