"""Provides classes for drawing labels."""

from typing import (
    Iterator,
    List,
    Optional,
    Tuple,
)

from cairo import (
    Context,
    ImageSurface,
)

from ..define import (
    DiagramAttributes,
    TextAttributes,
)

from ..geometry import Orientation
from ..util import class_str

from .functions import (
    font_slant,
    font_weight,
    new_surface,
    pt_to_px,
)

######################################################################

class Label:
    """Piece of text drawn on the diagram."""

    def __init__(
            self,
            text_attributes: TextAttributes,
            diagram_attributes: DiagramAttributes,
            orientation: Orientation,
            text: Optional[str] = None,
    ):
        """Initialize the label.

        It derives the text for the label from the text attributes,
        unless an explicit text is provided.

        The attributes of the diagram are used to calculate the
        dimensions of the label.

        A horizontal/vertical orientation must be explicitly given,
        since it cannot be derived from the text orientation in the
        attributes alone.

        """
        self._text_attributes = text_attributes
        if not text:
            text = text_attributes.label
        self._lines: List[str] = []
        if text:
            self._lines = text.split("\n")
        self._text = text
        self._diagram_attributes = diagram_attributes
        self._orientation = orientation
        width, height = self._calculate_dimensions()
        self._width = width
        self._height = height

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._text)
        return class_str(self, content)

    def __len__(self) -> int:
        """Return the number of lines."""
        return len(self._lines)

    @property
    def attributes(self) -> TextAttributes:
        """Attributes of the label."""
        return self._text_attributes

    @property
    def text(self) -> Optional[str]:
        """Text of the label."""
        return self._text

    def lines(self) -> Iterator[str]:
        """Iterate over the lines that make up the label."""
        yield from self._lines

    @property
    def orientation(self) -> Orientation:
        """Orientation of the text in the label."""
        return self._orientation

    def is_horizontal(self) -> bool:
        """True if the label is horizontal."""
        return self._orientation is Orientation.HORIZONTAL

    def is_vertical(self) -> bool:
        """True if the label is vertical."""
        return not self.is_horizontal()

    @property
    def width(self) -> float:
        """Width of the label.

        This does *not* take into account the orientation of the text!

        """
        return self._width

    @property
    def height(self) -> float:
        """Height of the label.

        This does *not* take into account the orientation of the text!

        """
        return self._height

    @property
    def box_width(self) -> float:
        """Width of the box enclosing the label.

        This *does* take into account the orientation of the text!

        """
        if self.is_vertical():
            return self._height
        return self._width

    @property
    def box_height(self) -> float:
        """Height of the box enclosing the label.

        This *does* take into account the orientation of the text!

        """
        if self.is_vertical():
            return self._width
        return self._height

    def new_context(self, surface: ImageSurface) -> Context:
        """Create a new context for drawing the label on the surface.

        It returns a Cairo context which is compatible with the one
        used to calculate the dimensions of the label.

        """
        ctx = Context(surface)
        attrs = self._text_attributes
        color = attrs.text_fill
        if color:
            ctx.set_source_rgba(*color.rgba)
        else:
            # No color = transparent text.
            ctx.set_source_rgba(0, 0, 0, 0)
        family = attrs.font_family
        slant = font_slant(attrs)
        weight = font_weight(attrs)
        ctx.select_font_face(family, slant, weight)
        ctx.set_font_size(pt_to_px(attrs.font_size))
        return ctx

    def _calculate_dimensions(self) -> Tuple[float, float]:
        """Calculate the dimensions of the label."""
        width = height = line_height = 0.0
        # We will calculate the dimensions using a temporary drawing
        # surface!
        scale = self._diagram_attributes.scale
        with new_surface(0, 0, scale) as surface:
            ctx = self.new_context(surface)
            lines = self._lines
            # Calculate the width.
            for line in lines:
                extents = ctx.text_extents(line)
                width = max(width, extents.width)
            # Calculate the height of a single line.  We assume that
            # the string "Mj" has the maximum height!
            line_height = ctx.text_extents("Mj").height
            # Calculate the total height.
            factor = self._text_attributes.text_line_height
            height = len(lines) * factor * line_height
        return width, height
