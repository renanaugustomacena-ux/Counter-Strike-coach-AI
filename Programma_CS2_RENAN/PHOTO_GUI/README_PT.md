> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets Graficos e Temas de UI

Este diretorio contem a infraestrutura visual para a aplicacao de coach do
Counter-Strike. Ele abriga wallpapers de alta resolucao, fontes personalizadas e
overviews de mapas usados pela GUI interativa Qt. Contem apenas assets -- nenhum
codigo.

## Visao Geral Tecnica

O sistema utiliza uma arquitetura baseada em temas para manter a consistencia
visual entre diferentes iteracoes do jogo (CS 1.6, CS:GO, CS2). Esses assets sao
carregados em tempo de execucao pelo frontend Qt: o motor de temas
(`apps/qt_app/core/theme_engine.py`) registra cinco fontes na inicializacao e
resolve os wallpapers selecionados pelo usuario na pasta do tema ativo (o padrao
de design e uma superficie plana sem wallpaper), e o widget nativo de mapa tatico
(`apps/qt_app/widgets/tactical/map_widget.py`) renderiza os overviews de `maps/`.
O uso de fontes vetorizadas e wallpapers com proporcoes consistentes mantem a UI
nitida em qualquer resolucao.

## Componentes Principais

### Temas de UI
O diretorio esta organizado em subdiretorios tematicos que definem o visual e a sensacao da aplicacao:
- **`cs16theme/`**: Estetica retro inspirada no Counter-Strike 1.6.
- **`csgotheme/`**: Visuais taticos modernos do Global Offensive.
- **`cs2theme/`**: Assets de proxima geracao adaptados para o Counter-Strike 2.

### Overviews de Mapas
O subdiretorio **`maps/`** contem 31 PNGs de visao geral de cima para baixo dos mapas competitivos:
- **`de_dust2.png`**, **`de_mirage.png`**, **`de_anubis.png`**, etc. (incluindo niveis inferiores para Nuke e Vertigo).
- Variacoes "`_dark`" e "`_light`" da maioria dos mapas para melhor contraste (Anubis atualmente tem apenas a variante base).

### Tipografia e Branding
Arquivos de fontes incluidos neste diretorio (cinco sao registrados na inicializacao pelo motor de temas; `NewHope-Line.ttf` e incluido mas nao esta no mapa de fontes do loader):
- **`cs_regular.ttf`**: Fonte iconica de branding no estilo CS.
- **`JetBrainsMono-Regular.ttf`**: Usada para dados tecnicos e logs de partida em estilo de codigo.
- **`Roboto-Regular.ttf`**: Texto padrao para descricoes de analise.
- **`NewHope.ttf`**: Fonte display (**`NewHope-Line.ttf`**: variante companion nao registrada).
- **`YUPIX.otf`**: Fonte display pixel retro.

O motor de temas tambem faz uma varredura automatica de um segundo stack de fontes display em `assets/fonts/` (Space Grotesk, Inter), portanto estas nao sao as unicas fontes do app.

## Estrutura do Diretorio

```text
Programma_CS2_RENAN/PHOTO_GUI/
├── cs16theme/              # Wallpapers CS 1.6 (retro)
├── cs2theme/               # Wallpapers CS2
├── csgotheme/              # Wallpapers CS:GO
├── maps/                   # PNGs de overview de mapas (base + variantes _dark/_light)
├── cs_regular.ttf          # Fonte de branding
├── JetBrainsMono-Regular.ttf # Fonte tecnica
├── NewHope.ttf / NewHope-Line.ttf # Fontes display
├── Roboto-Regular.ttf      # Fonte de texto
└── YUPIX.otf               # Fonte display pixel
```

## Uso

1. **Renderizacao de GUI**: O motor de temas registra cinco fontes na inicializacao. Wallpapers estao desativados por padrao (superficie plana); quando o usuario seleciona um em Configuracoes (configuracao `BACKGROUND_IMAGE` persistida), ele e resolvido dentro da pasta do tema ativo (`cs2theme/`, `csgotheme/`, `cs16theme/`). Um modo slideshow de wallpapers (`WALLPAPER_SLIDESHOW`) rotaciona as imagens na pasta do tema ativo.
2. **Sobreposicoes Taticas**: O widget nativo de mapa tatico (`TacticalMapWidget`) carrega os overviews `maps/*.png` e desenha posicoes de jogadores, trajetorias e marcadores sobre eles durante o replay 2D.
3. **Sons de UI Opcionais**: `apps/qt_app/core/sound.py` escaneia uma pasta opcional `PHOTO_GUI/sounds/` para arquivos WAV fornecidos pelo usuario; o app degrada silenciosamente se a pasta estiver ausente.
