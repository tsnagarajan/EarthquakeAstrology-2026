"""pipeline/features/regions.py

Assigns a seismic region label to a grid cell based on its (grid_lat, grid_lon)
5-degree cell coordinates, rather than the country string produced by
extract_country(). The country string is too coarse for several regions
(e.g. "Russia" spans both Kamchatka/Kuril — Pacific Ring — and western Russia
— not Pacific Ring — but extract_country() collapses both to "Russia").

Regions are defined as lat/lon bounding boxes and checked in order — the
first matching box wins. Two of the boxes below overlap on purpose:

  - Caribbean is fully contained within the Americas Pacific box, so
    Caribbean is checked first to keep it from being absorbed.
  - Mediterranean and Middle East overlap in a small sliver (roughly
    Cyprus / Levant / southern Turkey coast, lat 30-40, lon 34-37).
    Middle East is checked first per project decision.

Cells matching none of the boxes (mid-ocean ridges, Antarctica, etc.) are
"Unclassified".
"""

# (region_name, lat_min, lat_max, lon_min, lon_max) — order matters, first match wins.
# Dateline-crossing regions are represented as separate eastern/western boxes.
REGION_BOXES = [
    ("Caribbean", 8, 23, -88, -60),
    ("Middle East", 12, 40, 34, 60),
    ("Mediterranean", 30, 46, -6, 37),
    ("South Asia", 5, 38, 60, 92),
    ("Pacific Ring Asia/Oceania", -50, 55, 95, 180),
    ("Pacific Ring Asia/Oceania", -50, 55, -180, -160),
    ("Americas Pacific", -56, 60, -125, -60),
]


def assign_region_by_latlon(grid_lat: float, grid_lon: float) -> str:
    """Return the seismic region label for a (grid_lat, grid_lon) cell.

    Checks REGION_BOXES in order and returns the first matching region.
    Returns "Unclassified" if no box matches.
    """
    for region_name, lat_min, lat_max, lon_min, lon_max in REGION_BOXES:
        if lat_min <= grid_lat <= lat_max and lon_min <= grid_lon <= lon_max:
            return region_name
    return "Unclassified"
