# Visualização & Geração de Relatórios

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/reporting/`
**Proprietário:** camada de apresentação do Macena CS2 Analyzer

## Introdução

Este pacote transforma dados brutos de análise de partida em artefatos visuais legíveis
e relatórios estruturados. Ele se situa na camada mais externa da arquitetura, consumindo
saídas das pipelines de processamento, análise e coaching para produzir heatmaps,
overlays diferenciais, anotações de momentos críticos e relatórios Markdown
multi-seção. Todo o rendering é suportado por Matplotlib com gerenciamento
determinístico do ciclo de vida das figuras para prevenir vazamentos de memória.

## Inventário de Arquivos

| Arquivo | Propósito | Exports Principais |
|---------|-----------|-------------------|
| `visualizer.py` | Motor de visualização de mapas baseado em Matplotlib | `MatchVisualizer`, `generate_highlight_report()` |
| `report_generator.py` | Construtor de relatórios de partida multi-seção | `MatchReportGenerator` |
| `__init__.py` | Marcador de pacote | -- |

## Arquitetura & Conceitos

### Motor de Visualização de Mapas (`visualizer.py`)

`MatchVisualizer` é a classe central de rendering. Ela produz quatro categorias de saída
visual:

1. **Heatmaps de Posição** (`generate_heatmap`) -- histograma 2D das posições de
   jogadores sobreposto ao fundo do mapa. Usa uma grade de 64 bins com colourmap
   `"magma"` e limite mínimo de contagem (`cmin=1`) para suprimir bins vazios.

2. **Overlays Diferenciais** (`render_differential_overlay`) -- heatmap divergente
   comparando posicionamento do usuário contra baselines profissionais. O algoritmo:
   - Converte cada conjunto de posições em uma grade de densidade com `resolution`
     configurável (padrão 128).
   - Aplica desfoque Gaussiano (`sigma=5.0`) via `scipy.ndimage.gaussian_filter`.
   - Normaliza cada densidade independentemente, depois computa a diferença.
   - Mascara regiões com atividade insignificante (limiar `< 0.02`).
   - Renderiza com colourmap divergente `RdBu_r` e `TwoSlopeNorm` centrado em zero.
   - Regiões azuis indicam posicionamento pesado do usuário; regiões vermelhas indicam
     posicionamento pesado de profissionais.

3. **Mapas de Momentos Críticos** (`render_critical_moments`) -- scatter plot anotado
   de eventos-chave identificados pelo `ChronovisorScanner`. Cada momento é renderizado
   como marcador colorido por severidade, formatado por tipo e dimensionado por escala;
   os três atributos são campos independentes no dict de anotação:

   | Atributo | Mapeamento |
   |----------|------------|
   | Severidade → cor | critical = vermelho, significant = laranja, notable = ouro |
   | Tipo → marcador | play = `^` (triângulo para cima), mistake = `v` (triângulo para baixo) |
   | Escala → tamanho em pixels | micro = 100, standard = 200, macro = 350 |

4. **Gráficos de Erros por Round** (`plot_round_errors`) -- scatter plot marcando
   localizações de morte (vermelho `x`) e decisões ruins sinalizadas pelo coach
   (laranja `P`) para um único round.

Todos os métodos de rendering seguem o padrão **try/finally** (`DA-VZ-01`),
garantindo `plt.close(fig)` mesmo quando `savefig` lança exceção. Isso previne
vazamentos de figuras Matplotlib em condições de erro.

#### Fundo do Mapa & Limites

Imagens de fundo são carregadas de `assets/maps/` usando caminhos definidos em
`data/map_tensors.json`. Uma guarda de path traversal (`VZ-02`) valida que o caminho
de imagem resolvido permaneça dentro de `assets_dir` antes do carregamento. Seis mapas
possuem limites hardcoded em `_get_bounds()`: `de_mirage`, `de_inferno`, `de_dust2`,
`de_nuke`, `de_overpass` e `de_ancient`. Mapas desconhecidos recaem para bounding box
`(-4000, 4000, -4000, 4000)`.

### Gerador de Relatórios (`report_generator.py`)

`MatchReportGenerator` orquestra a pipeline completa de relatórios:

1. **Parse** -- carrega o arquivo demo via `DemoLoader`.
2. **Extração** -- itera os frames parseados para coletar posições de jogadores e
   eventos de morte.
3. **Visualização** -- chama `MatchVisualizer.generate_heatmap()` para produzir a
   heatmap de posicionamento.
4. **Escrita** -- produz um arquivo de relatório Markdown com timestamp contendo:
   - Nome do mapa e data de geração.
   - Imagem heatmap incorporada (caminho relativo, `RG-02`).
   - Seção de análise de erros fundamentais.

O diretório de saída é ancorado a `USER_DATA_ROOT/reports` com guarda de escape de
caminho (`RG-01`) garantindo que o relatório permaneça sob a raiz de dados do usuário.

#### Anotações de Segurança

| Código | Guarda |
|--------|--------|
| `DA-VZ-01` | Fechamento de figuras `try/finally` para prevenir vazamentos de memória |
| `VZ-02` | Prevenção de path traversal para imagens de fundo de mapa |
| `DA-RG-01` | Ancoragem de caminho absoluto para diretório de saída de relatórios |
| `RG-01` | Validação de escape de caminho garantindo saída sob `USER_DATA_ROOT` |
| `RG-02` | Caminho relativo em Markdown para evitar exposição da estrutura do filesystem |

### Integração de Highlight Report (`generate_highlight_report`)

A função a nível de módulo `generate_highlight_report(match_id, map_name)` conecta
o modelo RAP Coach com o motor de visualização. Ela:

1. Verifica se o modelo RAP está habilitado via `get_setting("USE_RAP_MODEL")`.
2. Instancia `ChronovisorScanner` e escaneia a partida em busca de momentos críticos.
3. Converte cada `CriticalMoment` em um dict de anotação highlight.
4. Renderiza a imagem de mapa anotada via `render_critical_moments()`.

Esta função é guardada por um amplo `try/except` com logging de erros, garantindo que
falhas de visualização nunca causem crash da pipeline chamadora.

## Integração

| Consumidor | Uso |
|------------|-----|
| `backend/services/coaching_service.py` | Instancia `MatchVisualizer` para overlays de relatórios estáticos |
| `backend/nn/rap_coach/chronovisor_scanner.py` | Fornece objetos `CriticalMoment` para rendering (importado por `generate_highlight_report()`) |
| `ingestion/demo_loader.py` | Fornece frames parseados consumidos por `MatchReportGenerator` |
| `core/config.py` | `USER_DATA_ROOT` para ancoragem de caminho de saída de relatórios |

## Formatos de Saída

| Formato | DPI | Caso de Uso |
|---------|-----|-------------|
| PNG | default (heatmaps, gráficos de round); 150 (overlays, mapas de momentos críticos) | Visualizações de mapas |
| Markdown | -- | Relatórios de texto estruturado com referências de imagens incorporadas |

## Notas de Desenvolvimento

- **Ciclo de vida das figuras**: cada figura Matplotlib deve ser criada e fechada no
  mesmo escopo de método. Nunca armazene referências de figuras como atributos de
  instância.
- **Saída determinística**: nomes de arquivo PNG derivam apenas do nome do mapa (ou
  ID do round), então re-renderizar o mesmo mapa sobrescreve a imagem anterior; apenas
  o relatório Markdown carrega um timestamp. Bins de heatmap e colourmap são fixos para
  reprodutibilidade.
- **Isolamento de dependências**: `scipy.ndimage.gaussian_filter` é a única importação
  do SciPy; `numpy` é usado para computação de grade. Ambos são dependências
  obrigatórias.
- **Testes**: o script smoke na raiz do repositório `tests/verify_reporting.py` instancia
  `MatchVisualizer` e `MatchReportGenerator` contra um diretório de saída temporário;
  `Programma_CS2_RENAN/tests/test_chronovisor_highlights.py` verifica que
  `render_critical_moments()` escreve um PNG válido.
