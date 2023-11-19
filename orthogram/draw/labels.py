"""Provides classes for drawing labels."""

from abc import ABC

from typing import (
    Iterator,
    Optional,
    Tuple,
)

from cairo import (
    Context,
    ImageSurface,
)

from cassowary import Variable  # type: ignore

from cassowary.expression import (  # type: ignore
    Constraint,
    Expression,
)

from ..arrange import WireLabel

from ..define import (
    ConnectionLabelPosition,
    DiagramAttributes,
    TextAttributes,
)

from ..geometry import Orientation
from ..util import class_str

from .functions import (
    arrow_width,
    font_slant,
    font_weight,
    new_surface,
    pt_to_px,
    wire_width,
)

######################################################################

class DrawingLabel:
    """Piece of text drawn on the diagram."""

    def __init__(
            self,
            text_attributes: TextAttributes,
            diagram_attributes: DiagramAttributes,
            orientation: Orientation,
    ):
        """Initialize the label.

        A horizontal/vertical orientation must be explicitly given,
        since it cannot be derived from the text orientation in the
        attributes alone.

        The attributes of the diagram are used to calculate the
        dimensions of the label.

        """
        self._text_attributes = text_attributes
        self._diagram_attributes = diagram_attributes
        self._orientation = orientation
        text = text_attributes.label
        if text:
            lines = text.split("\n")
        else:
            lines = []
        self._text = text
        self._lines = lines
        width, height = self._calculate_dimensions()
        self._width = width
        self._height = height

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._text)
        return class_str(self, content)

    def __bool__(self) -> bool:
        """The label is falsey if the text is empty."""
        return bool(self._lines)

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
    def attributes(self) -> TextAttributes:
        """Attributes of the label."""
        return self._text_attributes

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

######################################################################

class DrawingWireLabel(ABC):
    """Label on a drawing wire."""

    def __init__(
            self,
            layout_label: WireLabel,
            diagram_attributes: DiagramAttributes,
    ):
        """Initialize for the given layout label."""
        self._layout_label = layout_label
        self._drawing_label = DrawingLabel(
            text_attributes=layout_label.attributes,
            diagram_attributes=diagram_attributes,
            orientation=layout_label.orientation,
        )
        self._position = layout_label.position
        self._layout_segment = segment = layout_label.segment
        self._connection_attributes = segment.connection.attributes
        self._text_attributes = layout_label.attributes
        self._width_along, self._height_across = self._relative_dimensions()
        self._displacement = self._calculate_displacement()
        name = layout_label.name
        if segment.grid_vector.is_horizontal():
            coord_name = "x"
        else:
            coord_name = "y"
        var_name = f"label_{name}_{coord_name}"
        self._lmid = Variable(var_name)

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._layout_label.description()
        return class_str(self, content)

    @property
    def drawing_label(self) -> DrawingLabel:
        """The label to draw on the diagram."""
        return self._drawing_label

    @property
    def attributes(self) -> TextAttributes:
        """Attributes of the label."""
        return self._text_attributes

    @property
    def position(self) -> ConnectionLabelPosition:
        """Position of the label along the connection."""
        return self._position

    @property
    def displacement(self) -> Tuple[float, float]:
        """Distance of label center from connection axis."""
        return self._displacement

    def perpendicular_coverage(self) -> float:
        """Distance from 'highest' point to axis."""
        label = self._drawing_label
        gap = label.attributes.label_distance
        if self._layout_label.follows_segment():
            length = label.height
        else:
            length = label.width
        return self._bump() + gap + length

    @property
    def lmid(self) -> Variable:
        """Variable holding the middle coordinate along the axis."""
        return self._lmid

    @property
    def lmin(self) -> Expression:
        """Expression giving the minimum coordinate along the segment."""
        return self._lmid - 0.5 * self._width_along

    @property
    def lmax(self) -> Expression:
        """Expression giving the maximum coordinate along the segment."""
        return self._lmid + 0.5 * self._width_along

    def constraints(self) -> Iterator[Constraint]:
        """Override this to generate constraints for the solver."""
        yield from []

    def _relative_dimensions(self) -> Tuple[float, float]:
        """Dimensions relative to the orientation of the segment.

        Returns:

          1. Width parallel to the segment.
          2. Height perpendicular to the segment.

        """
        label = self._drawing_label
        if self._layout_label.follows_segment():
            return label.width, label.height
        return label.height, label.width

    def _calculate_displacement(self) -> Tuple[float, float]:
        """Calculate the displacement."""
        label = self._drawing_label
        gap = label.attributes.label_distance
        dist = self._bump() + gap
        segment = self._layout_segment
        if segment.grid_vector.is_horizontal():
            dist += 0.5 * label.box_height
            return 0.0, -dist
        dist += 0.5 * label.box_width
        return -dist, 0.0

    def _bump(self) -> float:
        """Offset needed to avoid other elements.

        The default implementation takes only the width of the wire
        into account.  Override to alter this behavior.

        """
        return self._wire_bump()

    def _wire_bump(self) -> float:
        """Offset needed to avoid the connection line."""
        return 0.5 * wire_width(self._connection_attributes)

######################################################################

class DrawingWireEndLabel(DrawingWireLabel):
    """Label at one end of a drawing wire."""

    def __init__(
            self,
            layout_label: WireLabel,
            diagram_attributes: DiagramAttributes,
    ):
        """Initialize for the given layout label."""
        assert not layout_label.position.is_middle()
        super().__init__(layout_label, diagram_attributes)

    def _bump(self) -> float:
        """Offset needed to avoid other elements.

        We have to override this, because the label may be over an
        arrow.

        """
        attrs = self._connection_attributes
        position = self._position
        if (
                (position.is_start() and attrs.arrow_back) or
                (position.is_end() and attrs.arrow_forward)
        ):
            return self._arrow_bump()
        return self._wire_bump()

    def _arrow_bump(self) -> float:
        """Offset needed to avoid the arrows."""
        return 0.5 * arrow_width(self._connection_attributes)

######################################################################

class DrawingWireMiddleLabel(DrawingWireLabel):
    """Label near the middle of a drawing wire."""

    def __init__(
            self,
            layout_label: WireLabel,
            diagram_attributes: DiagramAttributes,
            band_cmin: Variable, band_cmax: Variable
    ):
        """Initialize for the given layout label.

        This label will be drawn between the coordinates given by the
        two variables, which define the empty space between two
        consecutive bands.

        """
        assert layout_label.position.is_middle()
        super().__init__(layout_label, diagram_attributes)
        self._band_cmin = band_cmin
        self._band_cmax = band_cmax

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the label."""
        yield from self._band_constraints()

    def _band_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the bands on each side of the label."""
        # Center label between bands.
        yield self._lmid == 0.5 * (self._band_cmin + self._band_cmax)
        # Separate bands to fit the label.
        dist = self._text_attributes.label_distance
        total = self._width_along + 2 * dist
        yield self._band_cmax - self._band_cmin >= total
