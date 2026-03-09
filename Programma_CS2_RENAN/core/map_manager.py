"""
Map Manager - High-level interface for map assets.

Delegates to AssetAuthority for asset resolution and provides
async loading capabilities for Kivy applications.
"""

from kivy.loader import Loader

from Programma_CS2_RENAN.core.asset_manager import AssetAuthority, SmartAsset
from Programma_CS2_RENAN.core.spatial_data import get_map_metadata
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.map_manager")


class MapManager:
    """
    Manages map assets with async loading and spatial metadata integration.

    This is the recommended interface for UI components that need map visuals.
    It wraps AssetAuthority with Kivy-specific async loading support.
    """

    @staticmethod
    def get_map_path(map_name: str, theme: str = "regular") -> str:
        """
        Returns the absolute path to a map overview PNG.

        Args:
            map_name: Map identifier (e.g., "de_mirage")
            theme: Visual theme ("regular", "dark", "light")

        Returns:
            Absolute file path (may be fallback path if asset missing)
        """
        asset = AssetAuthority.get_map_asset(map_name, theme)
        return asset.path

    @staticmethod
    def get_map_asset(map_name: str, theme: str = "regular") -> SmartAsset:
        """
        Returns a SmartAsset for the map (includes path, texture, metadata).

        Args:
            map_name: Map identifier
            theme: Visual theme

        Returns:
            SmartAsset with lazy-loaded texture
        """
        return AssetAuthority.get_map_asset(map_name, theme)

    @staticmethod
    def load_map_async(map_name: str, callback, theme: str = "regular"):
        """
        Asynchronously loads a map texture.

        Args:
            map_name: Name of the map (e.g., 'de_dust2')
            callback: Function called when loading completes.
                      Signature: callback(loader, image_or_texture)
            theme: Visual theme

        Returns:
            ProxyImage that can be used for tracking load state
        """
        asset = AssetAuthority.get_map_asset(map_name, theme)

        if asset.is_fallback:
            # MM-01: Log warning when fallback asset is used — callers receive None
            # instead of a ProxyImage, which may affect load-state tracking.
            _logger.warning("MM-01: Map '%s' using fallback asset (no ProxyImage returned)", map_name)
            from kivy.clock import Clock

            Clock.schedule_once(lambda dt: callback(None, asset.texture), 0)
            return None

        proxy_image = Loader.image(asset.path)
        proxy_image.bind(on_load=callback)
        return proxy_image

    @staticmethod
    def get_map_metadata(map_name: str):
        """
        Helper to get spatial metadata for a map.

        Returns:
            MapMetadata with bounds, scale, and projection info
        """
        return get_map_metadata(map_name)
