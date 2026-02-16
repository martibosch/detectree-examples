"""Utils."""


def swissimage_asset_id_to_tile_id(asset_id_ser):
    """Extract tile IDs from SWISSIMAGE asset IDs."""
    return asset_id_ser.str.split("_").str[-1]


def surface3d_asset_id_to_tile_id(asset_id_ser):
    """Extract tile IDs from swissSURFACE3D asset IDs."""
    return asset_id_ser.str.split("_").str[-3]
