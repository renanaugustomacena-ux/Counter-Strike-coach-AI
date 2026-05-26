> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets Gráficos e Temas de UI

Este diretório contém a infraestrutura visual para a aplicação de coach do Counter-Strike. Ele abriga assets de alta resolução, fontes personalizadas e visões gerais de mapas (overviews) usados para gerar tanto a GUI interativa quanto os relatórios profissionais de análise em PDF.

## Visão Geral Técnica

O sistema utiliza uma arquitetura baseada em temas para manter a consistência visual entre diferentes iterações do jogo (CS 1.6, CS:GO, CS2). Esses assets são carregados dinamicamente pelo módulo de `reporting` para sobrepor dados táticos (posições de smoke, caminhos dos jogadores) sobre as imagens dos mapas. O uso de fontes vetorizadas e wallpapers com proporções consistentes garante que os relatórios gerados sejam de alta qualidade e legíveis.

## Componentes Principais

### Temas de UI
O diretório está organizado em subdiretórios temáticos que definem o visual e a sensação da aplicação:
- **`cs16theme/`**: Estética retrô inspirada no Counter-Strike 1.6.
- **`csgotheme/`**: Visuais táticos modernos do Global Offensive.
- **`cs2theme/`**: Assets de próxima geração adaptados para o Counter-Strike 2.

### Overviews de Mapas
O subdiretório **`maps/`** contém visões de radar e visões gerais para todos os mapas do serviço ativo:
- **`de_dust2.png`**, **`de_mirage.png`**, etc.
- Suporte para variações nos modos "Dark" (escuro) e "Light" (claro) para melhor contraste nos relatórios.

### Tipografia e Branding
Fontes essenciais para renderização de UI e geração de PDF:
- **`cs_regular.ttf`**: Fonte icônica de branding no estilo CS.
- **`JetBrainsMono-Regular.ttf`**: Usada para dados técnicos e logs de partida em estilo de código.
- **`Roboto-Regular.ttf`**: Texto padrão para descrições de análise.

## Estrutura do Diretório

```text
Programma_CS2_RENAN/PHOTO_GUI/
├── cs16theme/              # Assets legados
├── cs2theme/               # Assets modernos do CS2
├── csgotheme/              # Assets no estilo CS:GO
├── maps/                   # Overviews de mapas para sobreposições táticas
├── cs_regular.ttf          # Fonte de branding
├── JetBrainsMono-Regular.ttf # Fonte técnica
└── ... (outros assets)
```

## Uso

1. **Renderização de GUI**: O painel principal utiliza os wallpapers e temas para fornecer uma experiência de usuário imersiva.
2. **Sobreposições Táticas**: Durante a análise, o sistema seleciona um mapa de `maps/` e desenha programaticamente trajetórias de utilitários e heatmaps sobre ele.
3. **Geração de PDF**: O motor de relatórios utiliza os assets aqui para compilar relatórios finais de sessão, garantindo que cada PDF tenha um layout profissional consistente, independentemente do mapa analisado.
