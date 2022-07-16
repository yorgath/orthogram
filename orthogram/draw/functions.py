"""Auxiliary functions for diagram drawing."""

import math

from cairo import (
    FontSlant as CairoFontSlant,
    FontWeight as CairoFontWeight,
    Format,
    ImageSurface,
)

from shapely.geometry import (  # type: ignore
    JOIN_STYLE,
    Polygon,
)

from ..define import (
    AreaAttributes,
    AttributeMap,
    ConnectionAttributes,
    FontStyle,
    FontWeight,
    LineAttributes,
    TextAttributes,
)

######################################################################

def new_surface(width: float, height: float, scale: float) -> ImageSurface:
    """Return a new surface having the requested dimensions."""
    surf_width = math.ceil(scale * width)
    surf_height = math.ceil(scale * height)
    surface = ImageSurface(Format.ARGB32, surf_width, surf_height)
    surface.set_device_scale(scale, scale)
    return surface

def pt_to_px(points: float) -> float:
    """Convert points to pixels (a.k.a. user or device units)."""
    return 1.25 * points

def buffer_rectangle(poly: Polygon, distance: float) -> Polygon:
    """Create a buffer around a rectangular polygon.

    It can handle degenerate cases, i.e. polygons with zero area.

    """
    # We return the envelope of the result, because degenerate
    # polygons may turn into triangular buffers!
    return poly.buffer(distance, join_style=JOIN_STYLE.mitre).envelope

def line_buffer_attributes(attrs: ConnectionAttributes) -> LineAttributes:
    """Extract the buffer attributes as line attributes."""
    color = attrs.buffer_fill
    buffer_width = attrs.buffer_width
    if buffer_width:
        width = attrs.stroke_width + 2 * buffer_width
    else:
        width = 0.0
    attr_map: AttributeMap = {
        'stroke': color,
        'stroke_width': width,
    }
    line_attrs = LineAttributes()
    line_attrs.set_attributes(**attr_map)
    return line_attrs

def line_area_attributes(attrs: LineAttributes) -> AreaAttributes:
    """Convert line attributes to area attributes."""
    attr_map: AttributeMap = {
        'fill': attrs.stroke,
    }
    area_attrs = AreaAttributes()
    area_attrs.set_attributes(**attr_map)
    return area_attrs

def wire_width(attrs: ConnectionAttributes) -> float:
    """Return the width of the wire, including the margin."""
    stroke_width = attrs.stroke_width
    buffer_width = attrs.buffer_width
    return stroke_width + 2 * buffer_width

def arrow_length(attrs: ConnectionAttributes) -> float:
    """Calculate the length of the arrow from the attributes."""
    width = arrow_width(attrs)
    aspect = attrs.arrow_aspect
    return width * aspect

def arrow_width(attrs: ConnectionAttributes) -> float:
    """Calculate the width of the arrow from the attributes."""
    return attrs.stroke_width * attrs.arrow_base

def font_slant(attrs: TextAttributes) -> CairoFontSlant:
    """Return the Cairo font slant from the attributes."""
    style = attrs.font_style
    if style is FontStyle.ITALIC:
        return CairoFontSlant.ITALIC
    if style is FontStyle.OBLIQUE:
        return CairoFontSlant.OBLIQUE
    return CairoFontSlant.NORMAL

def font_weight(attrs: TextAttributes) -> CairoFontWeight:
    """Return the Cairo font weight from the attributes."""
    weight = attrs.font_weight
    if weight is FontWeight.BOLD:
        return CairoFontWeight.BOLD
    return CairoFontWeight.NORMAL
