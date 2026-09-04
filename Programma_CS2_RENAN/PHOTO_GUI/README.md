> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Graphical Assets & UI Themes

This directory contains the visual infrastructure for the Counter-Strike coach application. It houses high-resolution wallpapers, custom fonts, and map overviews used by the interactive Qt GUI. It contains assets only — no code.

## Technical Overview

The system uses a theme-based architecture to maintain visual consistency across different game iterations (CS 1.6, CS:GO, CS2). These assets are loaded at runtime by the Qt frontend: the theme engine (`apps/qt_app/core/theme_engine.py`) registers five of the fonts at startup and resolves user-selected wallpapers from the active theme's folder (the design default is a flat surface with no wallpaper), and the native tactical map widget (`apps/qt_app/widgets/tactical/map_widget.py`) renders the `maps/` overviews. The use of vectorized fonts and consistent aspect-ratio wallpapers keeps the UI crisp at any resolution.

## Key Components

### UI Themes
The directory is organized into thematic subdirectories that define the look and feel of the application:
- **`cs16theme/`**: Retro aesthetics inspired by Counter-Strike 1.6.
- **`csgotheme/`**: Modern tactical visuals from Global Offensive.
- **`cs2theme/`**: Next-gen assets tailored for Counter-Strike 2.

### Map Overviews
The **`maps/`** subdirectory contains top-down overview PNGs for the competitive maps:
- **`de_dust2.png`**, **`de_mirage.png`**, etc. (including lower levels for Nuke and Vertigo).
- "`_dark`" and "`_light`" variations of most maps for better contrast.

### Typography & Branding
Font files shipped in this directory (five are registered at startup by the theme engine; `NewHope-Line.ttf` ships alongside but is not in the loader's font map):
- **`cs_regular.ttf`**: Iconic CS-style branding font.
- **`JetBrainsMono-Regular.ttf`**: Used for technical data and code-style match logs.
- **`Roboto-Regular.ttf`**: Standard body text for analysis descriptions.
- **`NewHope.ttf`**: Display font (**`NewHope-Line.ttf`**: unregistered companion variant).
- **`YUPIX.otf`**: Retro pixel display font.

The theme engine also auto-scans a second display-font stack under `assets/fonts/` (Space Grotesk, Inter), so these are not the app's only fonts.

## Directory Structure

```text
Programma_CS2_RENAN/PHOTO_GUI/
├── cs16theme/              # CS 1.6 wallpapers (retro)
├── cs2theme/               # CS2 wallpapers
├── csgotheme/              # CS:GO wallpapers
├── maps/                   # Map overview PNGs (base + _dark/_light variants)
├── cs_regular.ttf          # Branding font
├── JetBrainsMono-Regular.ttf # Technical font
├── NewHope.ttf / NewHope-Line.ttf # Display fonts
├── Roboto-Regular.ttf      # Body text font
└── YUPIX.otf               # Pixel display font
```

## Usage

1. **GUI Rendering**: The theme engine registers five fonts at startup. Wallpapers are off by default (flat surface); when the user picks one in Settings (persisted `BACKGROUND_IMAGE` setting), it is resolved inside the active theme's folder (`cs2theme/`, `csgotheme/`, `cs16theme/`).
2. **Tactical Overlays**: The native tactical map widget (`TacticalMapWidget`) loads the `maps/*.png` overviews and draws player positions, trajectories, and markers on top of them during 2D replay.
3. **Optional UI Sounds**: `apps/qt_app/core/sound.py` scans an optional `PHOTO_GUI/sounds/` folder for user-supplied WAV files; the app degrades silently if it is absent.
