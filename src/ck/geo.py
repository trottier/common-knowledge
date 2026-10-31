"""Shared Web Mercator viewports and coordinate labels for atlas/grid references."""

import math
from dataclasses import asdict, dataclass


def mercator(longitude: float, latitude: float) -> tuple[float, float]:
    if not (-90 < latitude < 90) or not all(map(math.isfinite, (longitude, latitude))):
        raise ValueError("Invalid geographic coordinate")
    return (longitude + 180) / 360, (1 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2


def unproject(x: float, y: float) -> tuple[float, float]:
    return x * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y))))


def wrap_longitude(longitude: float) -> float:
    return (longitude + 180) % 360 - 180


def dms(value: float, axis: str) -> str:
    if axis not in {"lat", "lon"} or not math.isfinite(value):
        raise ValueError("Invalid coordinate label")
    if axis == "lon":
        value = wrap_longitude(value)
    elif not -90 <= value <= 90:
        raise ValueError("Latitude outside bounds")
    degrees, remainder = divmod(round(abs(value) * 3600), 3600)
    minutes, seconds = divmod(remainder, 60)
    hemisphere = ("N" if value >= 0 else "S") if axis == "lat" else ("E" if value >= 0 else "W")
    return f"{degrees}°{minutes:02d}′{seconds:02d}″{hemisphere}"


def shifted_geometry(geometry):
    """Unwrap dateline counties before fitting a view; source bytes stay unchanged."""
    from shapely.ops import transform

    west, _, east, _ = geometry.bounds
    if east > 180:
        return geometry, True
    if east - west <= 180:
        return geometry, False

    def shift(x, y, z=None):
        # Shapely may invoke the transform with arrays or individual values.
        try:
            return tuple(value + 360 if value < 0 else value for value in x), y
        except TypeError:
            return x + 360 if x < 0 else x, y

    return transform(shift, geometry), True


@dataclass(frozen=True)
class Frame:
    west: float
    north: float
    east: float
    south: float
    width: int
    height: int
    columns: int
    rows: int
    shifted: bool = False

    @classmethod
    def fit(cls, geometry, *, width, height, columns, rows, padding, maxzoom):
        if width <= 0 or height <= 0 or not 1 <= columns <= 26 or rows <= 0 or padding < 0:
            raise ValueError("Invalid atlas frame settings")
        geometry, shifted = shifted_geometry(geometry)
        lon_west, lat_south, lon_east, lat_north = geometry.bounds
        west, south = mercator(lon_west, lat_south)
        east, north = mercator(lon_east, lat_north)
        center_x, center_y = (west + east) / 2, (north + south) / 2
        span = max(
            (east - west) * (1 + 2 * padding),
            (south - north) * width / height * (1 + 2 * padding),
            width / (512 * 2**maxzoom),
        )
        half_x, half_y = span / 2, span * height / width / 2
        return cls(
            center_x - half_x,
            center_y - half_y,
            center_x + half_x,
            center_y + half_y,
            width,
            height,
            columns,
            rows,
            shifted,
        )

    @property
    def center(self) -> list[float]:
        longitude, latitude = unproject((self.west + self.east) / 2, (self.north + self.south) / 2)
        return [wrap_longitude(longitude), latitude]

    @property
    def zoom(self) -> float:
        return round(math.log2(self.width / (512 * (self.east - self.west))), 10)

    def pixel(self, longitude: float, latitude: float) -> tuple[float, float]:
        if self.shifted and longitude < 0:
            longitude += 360
        x, y = mercator(longitude, latitude)
        return (
            (x - self.west) * self.width / (self.east - self.west),
            (y - self.north) * self.height / (self.south - self.north),
        )

    def grid(self, longitude: float, latitude: float) -> str:
        x, y = self.pixel(longitude, latitude)
        if not -1e-7 <= x <= self.width + 1e-7 or not -1e-7 <= y <= self.height + 1e-7:
            raise ValueError("Place outside its atlas frame")
        column = min(self.columns - 1, max(0, int(x * self.columns / self.width)))
        row = min(self.rows - 1, max(0, int(y * self.rows / self.height)))
        return f"{chr(65 + column)}{row + 1}"

    def labels(self) -> dict:
        vertical = []
        horizontal = []
        for index in range(self.columns + 1):
            longitude, _ = unproject(
                self.west + index * (self.east - self.west) / self.columns, self.north
            )
            vertical.append(
                {
                    "pixel": index * self.width / self.columns,
                    "decimal": f"{wrap_longitude(longitude):.4f}°",
                    "dms": dms(longitude, "lon"),
                }
            )
        for index in range(self.rows + 1):
            _, latitude = unproject(
                self.west, self.north + index * (self.south - self.north) / self.rows
            )
            horizontal.append(
                {
                    "pixel": index * self.height / self.rows,
                    "decimal": f"{latitude:.4f}°",
                    "dms": dms(latitude, "lat"),
                }
            )
        return {"vertical": vertical, "horizontal": horizontal}

    def as_dict(self) -> dict:
        return asdict(self)
