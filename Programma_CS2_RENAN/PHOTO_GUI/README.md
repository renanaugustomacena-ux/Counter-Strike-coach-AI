> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Graphical Assets & UI Themes

This directory contains the visual infrastructure for the Counter-Strike coach application. It houses high-resolution assets, custom fonts, and map overviews used to generate both the interactive GUI and the professional PDF analysis reports.

## Technical Overview

The system uses a theme-based architecture to maintain visual consistency across different game iterations (CS 1.6, CS:GO, CS2). These assets are dynamically loaded by the `reporting` module to overlay tactical data (smoke positions, player paths) onto map overviews. The use of vectorized fonts and consistent aspect-ratio wallpapers ensures that generated reports are high-quality and readable.

## Key Components

### UI Themes
The directory is organized into thematic subdirectories that define the look and feel of the application:
- **`cs16theme/`**: Retro aesthetics inspired by Counter-Strike 1.6.
- **`csgotheme/`**: Modern tactical visuals from Global Offensive.
- **`cs2theme/`**: Next-gen assets tailored for Counter-Strike 2.

### Map Overviews
The **`maps/`** subdirectory contains top-down radar views and overviews for all active-duty maps:
- **`de_dust2.png`**, **`de_mirage.png`**, etc.
- Support for "Dark" and "Light" mode variations for better contrast in reports.

### Typography & Branding
Essential fonts for UI rendering and PDF generation:
- **`cs_regular.ttf`**: Iconic CS-style branding font.
- **`JetBrainsMono-Regular.ttf`**: Used for technical data and code-style match logs.
- **`Roboto-Regular.ttf`**: Standard body text for analysis descriptions.

## Directory Structure

```text
Programma_CS2_RENAN/PHOTO_GUI/
├── cs16theme/              # Legacy assets
├── cs2theme/               # Modern CS2 assets
├── csgotheme/              # CS:GO style assets
├── maps/                   # Map overviews for tactical overlays
├── cs_regular.ttf          # Branding font
├── JetBrainsMono-Regular.ttf # Technical font
└── ... (other assets)
```

## Usage

1. **GUI Rendering**: The main dashboard uses the wallpapers and themes to provide an immersive user experience.
2. **Tactical Overlays**: During analysis, the system selects a map from `maps/` and programmatically draws utility trajectories and heatmaps on top of it.
3. **PDF Generation**: The reporting engine utilizes the assets here to compile final session reports, ensuring that every PDF has a consistent professional layout regardless of the map analyzed.
