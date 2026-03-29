"""
Unified Asset Authority for Macena CS2 Analyzer.

Consolidates the former `AsyncMapRegistry` and `MapAssetManager` into a single source of truth
for all map visual assets. Implements TASK 3.1 and 4.1 from Gemini_argument_core.md.

Features:
- SmartAsset dataclass with path, texture, theme metadata
- Singleton AssetAuthority for consistent access
- Checkered fallback texture for missing assets (not Mirage)
- Theme variant support (regular, dark, light)
- Lazy-loaded Kivy textures for performance
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional

try:
    from kivy.graphics.texture import Texture
except ImportError:
    Texture = None  # Headless / Qt-only mode — Kivy texture ops unavailable

from Programma_CS2_RENAN.core.config import get_resource_path
from Programma_CS2_RENAN.core.spatial_data import SPATIAL_REGISTRY, get_map_metadata
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.asset_manager")


@dataclass
class SmartAsset:
    """
    Unified asset container providing both file path and Kivy texture.

    Attributes:
        path: Absolute path to the asset file
        theme: Asset theme variant ("regular", "dark", "light")
        is_fallback: True if this is a generated fallback, not a real asset
        _texture: Lazily loaded Kivy texture (access via .texture property)
    """

    path: str
    theme: str = "regular"
    is_fallback: bool = False
    _texture: Optional[Texture] = field(default=None, repr=False)

    @property
    def texture(self) -> Optional[Texture]:
        """Lazy-load the Kivy texture on first access."""
        if self._texture is not None:
            return self._texture

        if self.is_fallback:
            # Generate checkered fallback texture
            self._texture = AssetAuthority._generate_checkered_texture()
        elif os.path.exists(self.path):
            # Load from file
            try:
                from kivy.core.image import Image as CoreImage

                img = CoreImage(self.path)
                self._texture = img.texture
            except Exception as e:
                _logger.warning("Failed to load texture %s: %s", self.path, e)
                self._texture = AssetAuthority._generate_checkered_texture()
        else:
            self._texture = AssetAuthority._generate_checkered_texture()

        return self._texture

    @property
    def exists(self) -> bool:
        """Check if the underlying file exists."""
        return os.path.exists(self.path) and not self.is_fallback


class AssetAuthority:
    """
    Singleton authority for all map visual assets.

    Replaces the former fragmented system of:
    - AsyncMapRegistry (asset_loader.py) - Kivy textures with checkered fallback
    - MapAssetManager (asset_manager.py) - File paths with Mirage fallback
    - MapManager (map_manager.py) - Wrapper with async loading

    Usage:
        asset = AssetAuthority.get_map_asset("de_mirage", theme="regular")
        path = asset.path  # Absolute file path
        tex = asset.texture  # Kivy Texture (lazy-loaded)
    """

    _instance = None
    # F6-32: _cache is class-level (shared across all instances). AssetAuthority is a
    # singleton (see __new__), so this is safe — all callers share one instance. If
    # multiple instances are ever created this cache must move to instance level.
    _cache: Dict[str, SmartAsset] = {}
    _fallback_texture: Optional[Texture] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_maps_directory(cls) -> str:
        """Returns the absolute path to the maps asset directory."""
        return get_resource_path(os.path.join("PHOTO_GUI", "maps"))

    @classmethod
    def get_map_asset(cls, map_name: str, theme: str = "regular") -> SmartAsset:
        """
        Retrieves a SmartAsset for the specified map.

        Args:
            map_name: Map identifier (e.g., "de_mirage", "mirage", "de_dust2.dem")
            theme: Visual theme ("regular", "dark", "light")

        Returns:
            SmartAsset with path, texture access, and metadata
        """
        # Normalize map name
        canonical_name = cls._normalize_map_name(map_name)
        cache_key = f"{canonical_name}:{theme}"

        # Check cache
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # Build file path with theme suffix
        suffix = ""
        if theme == "dark":
            suffix = "_dark"
        elif theme == "light":
            suffix = "_light"

        filename = f"{canonical_name}{suffix}.png"
        full_path = os.path.join(cls.get_maps_directory(), filename)

        # Check if themed version exists
        if os.path.exists(full_path):
            asset = SmartAsset(path=full_path, theme=theme, is_fallback=False)
        # Try fallback to regular theme
        elif theme != "regular":
            regular_path = os.path.join(cls.get_maps_directory(), f"{canonical_name}.png")
            if os.path.exists(regular_path):
                asset = SmartAsset(path=regular_path, theme="regular", is_fallback=False)
            else:
                asset = cls._create_fallback_asset()
        else:
            asset = cls._create_fallback_asset()

        # Cache and return
        cls._cache[cache_key] = asset
        return asset

    @classmethod
    def _normalize_map_name(cls, map_name: str) -> str:
        """
        Normalizes various map name formats to canonical form.

        Handles: "mirage", "de_mirage", "de_mirage.dem", "maps/de_mirage"
        Returns: "de_mirage"
        """
        if not map_name:
            return "unknown"

        clean = map_name.lower().strip()
        clean = clean.replace(".dem", "").replace(".vpk", "").replace("maps/", "")

        # Direct match in registry
        if clean in SPATIAL_REGISTRY:
            return clean

        # Try adding de_ prefix
        if f"de_{clean}" in SPATIAL_REGISTRY:
            return f"de_{clean}"

        # Partial match
        for key in SPATIAL_REGISTRY:
            if key in clean or clean in key:
                return key

        return clean if clean else "unknown"

    @classmethod
    def _create_fallback_asset(cls) -> SmartAsset:
        """Creates a fallback SmartAsset with checkered texture."""
        # Path doesn't exist, but we need something for logging
        fallback_path = os.path.join(cls.get_maps_directory(), "FALLBACK_CHECKERED")
        return SmartAsset(path=fallback_path, theme="fallback", is_fallback=True)

    @classmethod
    def _generate_checkered_texture(cls) -> Texture:
        """
        Generates a 64x64 magenta/black checkerboard texture for missing assets.

        This is superior to the old "Mirage fallback" because:
        1. It clearly indicates a missing asset (not false data)
        2. It's visually distinct and cannot be confused with real content
        3. It aids debugging by making gaps immediately visible
        """
        if cls._fallback_texture is not None:
            return cls._fallback_texture

        size = 64
        buf = bytearray(size * size * 3)

        for y in range(size):
            for x in range(size):
                # 8x8 checker pattern
                is_magenta = ((x // 8) + (y // 8)) % 2 == 0
                idx = (y * size + x) * 3
                if is_magenta:
                    buf[idx] = 255  # R
                    buf[idx + 1] = 0  # G
                    buf[idx + 2] = 255  # B
                else:
                    buf[idx] = 0
                    buf[idx + 1] = 0
                    buf[idx + 2] = 0

        texture = Texture.create(size=(size, size), colorfmt="rgb")
        texture.blit_buffer(bytes(buf), colorfmt="rgb", bufferfmt="ubyte")
        cls._fallback_texture = texture
        return texture

    @classmethod
    def clear_cache(cls):
        """Clears the asset cache. Useful for hot-reloading during development."""
        cls._cache.clear()
        cls._fallback_texture = None


# =============================================================================
# Backward Compatibility Layer
# =============================================================================
# These classes maintain compatibility with existing code during migration.
# They delegate to AssetAuthority and should be removed in a future cleanup.


class MapAssetManager:
    """
    DEPRECATED: Use AssetAuthority.get_map_asset() instead.
    Maintained for backward compatibility.
    """

    @staticmethod
    def get_map_source(map_name: str) -> str:
        """Returns file path for a map. Delegates to AssetAuthority."""
        asset = AssetAuthority.get_map_asset(map_name)
        return asset.path

    @staticmethod
    def _get_fallback() -> str:
        """Returns fallback path. Now uses checkered instead of Mirage."""
        return AssetAuthority._create_fallback_asset().path
