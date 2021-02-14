"""Provides classes for arranging diagram connections."""

from typing import (
    Iterator,
    List,
    Optional,
    Tuple,
)

from cassowary import Variable # type: ignore
from cassowary.expression import Constraint # type: ignore

from shapely.geometry import LineString # type: ignore

from ..define import ConnectionAttributes

from ..arrange import (
    Wire,
    WireSegment,
)

from ..geometry import (
    Orientation,
    OrientedObject,
)

from .labels import Label
from .names import Named

######################################################################

class DrawingWireLabel:
    """Label on a drawing wire."""

    def __init__(self, label: Label, cmin: Variable, cmax: Variable):
        """Initialize for a given drawing label."""
        self._drawing_label = label
        self._cmin = cmin
        self._cmax = cmax

    @property
    def drawing_label(self) -> Label:
        """The label to draw on the diagram."""
        return self._drawing_label

    @property
    def cmin(self) -> Variable:
        """Minimum coordinate along the segment."""
        return self._cmin

    @property
    def cmax(self) -> Variable:
        """Maximum coordinate along the segment."""
        return self._cmax

######################################################################

class DrawingWireSegment(OrientedObject):
    """Augments a layout wire segment."""

    def __init__(self, layout_segment: WireSegment):
        """Initialize for the given layout segment."""
        self._layout_segment = layout_segment
        self._wire_width = self._calculate_wire_width()
        # These will be set later during the process.
        self._label: Optional[DrawingWireLabel] = None
        self._x1: Variable
        self._y1: Variable
        self._x2: Variable
        self._y2: Variable

    def _calculate_wire_width(self) -> float:
        """Calculate the width of the wire itself, including buffer."""
        attrs = self.attributes
        width = attrs.stroke_width
        buffer_width = attrs.buffer_width
        if buffer_width:
            width += 2 * buffer_width
        return width

    @property
    def layout_segment(self) -> WireSegment:
        """The layout wire segment wrapped by this object."""
        return self._layout_segment

    @property
    def wire_width(self) -> float:
        """Width of the connection wire."""
        return self._wire_width

    @property
    def label(self) -> Optional[DrawingWireLabel]:
        """The label attached to the segment."""
        return self._label

    @label.setter
    def label(self, label: DrawingWireLabel) -> None:
        """Set the label."""
        self._label = label

    @property
    def label_displacement(self) -> Tuple[float, float]:
        """Vector from middle of segment to center of label."""
        width = self._wire_width
        disp = -0.5 * (width + self.margin_before)
        if self.is_horizontal():
            return (0.0, disp)
        return (disp, 0.0)

    @property
    def margin_before(self) -> float:
        """Margin before the line."""
        # Label is always before the line.
        return self._calculate_label_margin()

    @property
    def margin_after(self) -> float:
        """Margin after the line."""
        # There is nothing after the line.
        return 0.0

    def _calculate_label_margin(self) -> float:
        """Calculate a margin large enough for the label."""
        margin = 0.0
        wire_label = self._label
        if wire_label:
            label = wire_label.drawing_label
            margin += self.attributes.label_distance
            if self.is_horizontal():
                margin += label.box_height
            else:
                margin += label.box_width
        return margin

    @property
    def x1(self) -> Variable:
        """Coordinate of first point along the horizontal axis."""
        return self._x1

    @x1.setter
    def x1(self, var: Variable) -> None:
        """Set the variable."""
        self._x1 = var

    @property
    def y1(self) -> Variable:
        """Coordinate of first point along the vertical axis."""
        return self._y1

    @y1.setter
    def y1(self, var: Variable) -> None:
        """Set the variable."""
        self._y1 = var

    @property
    def x2(self) -> Variable:
        """Coordinate of second point along the horizontal axis."""
        return self._x2

    @x2.setter
    def x2(self, var: Variable) -> None:
        """Set the variable."""
        self._x2 = var

    @property
    def y2(self) -> Variable:
        """Coordinate of second point along the vertical axis."""
        return self._y2

    @y2.setter
    def y2(self, var: Variable) -> None:
        """Set the variable."""
        self._y2 = var

    @property
    def orientation(self) -> Orientation:
        """Orientation of the segment."""
        return self._layout_segment.orientation

    @property
    def attributes(self) -> ConnectionAttributes:
        """Attributes of the underlying connection."""
        return self._layout_segment.connection.attributes

######################################################################

class DrawingWire:
    """Augments a layout wire."""

    def __init__(self, layout_wire: Wire) -> None:
        """Initialize an empty wire."""
        self._layout_wire = layout_wire
        self._segments: List[DrawingWireSegment] = []

    @property
    def layout_wire(self) -> Wire:
        """The layout wire wrapped by this object."""
        return self._layout_wire

    def append_segment(self, segment: DrawingWireSegment) -> None:
        """Append segment to the wire."""
        self._segments.append(segment)

    def segments(self) -> Iterator[DrawingWireSegment]:
        """Return the segments that make up this wire."""
        yield from self._segments

    @property
    def line_string(self) -> LineString:
        """Return a line string for drawing the connection."""
        points: List[Tuple[float, float]] = []
        for seg in self._segments:
            if not points:
                point_1 = (seg.x1.value, seg.y1.value)
                points.append(point_1)
            point_2 = (seg.x2.value, seg.y2.value)
            points.append(point_2)
        return LineString(points)

    @property
    def attributes(self) -> ConnectionAttributes:
        """Attributes of the underlying connection."""
        return self._layout_wire.connection.attributes

######################################################################

class DrawingNetwork:
    """Augments a layout network."""

    def __init__(self) -> None:
        """Initialize an empty network."""
        self._wires: List[DrawingWire] = []

    def append_wire(self, wire: DrawingWire) -> None:
        """Add a wire to the network."""
        self._wires.append(wire)

    def wires(self) -> Iterator[DrawingWire]:
        """Return the wires."""
        yield from self._wires

######################################################################

class Lane(Named):
    """Corresponds to a wire drawing offset.

    Many connection wire segments may pass through it.

    """

    def __init__(self, band_name: str, band_index: int, offset: int):
        """Initialize an empty lane."""
        name = self._generate_name(band_name, offset)
        super().__init__(name)
        self._index = band_index
        self._offset = offset
        self._cmin = Variable(f"{name}_min")
        self._cref = Variable(f"{name}_ref")
        self._cmax = Variable(f"{name}_max")
        self._segments: List[DrawingWireSegment] = []

    @staticmethod
    def _generate_name(parent_name: str, offset: int) -> str:
        """Generate a unique name for the object."""
        ostr = str(offset).replace("-", "m")
        return f"{parent_name}_lane_{ostr}"

    @property
    def sort_key(self) -> Tuple[int, int]:
        """Key appropriate for sorting lanes."""
        return (self._index, self._offset)

    def add_wire(self, segment: DrawingWireSegment) -> None:
        """Route a wire through the lane."""
        self._segments.append(segment)

    def has_wire_end_at(self, coord: int) -> bool:
        """Return true if there is a segment end at the coordinate."""
        for dseg in self._segments:
            for seg_coord in dseg.layout_segment.coordinates:
                if seg_coord == coord:
                    return True
        return False

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the solver."""
        yield self._cmin == self._cref - self.width_before
        yield self._cmax == self._cref + self.width_after

    @property
    def total_width(self) -> float:
        """Total width of the lane."""
        return self.margin_before + self.wire_width + self.margin_after

    @property
    def width_before(self) -> float:
        """Width before the reference line."""
        return 0.5 * self.wire_width + self.margin_before

    @property
    def width_after(self) -> float:
        """Width after the reference line."""
        return 0.5 * self.wire_width + self.margin_after

    @property
    def wire_width(self) -> float:
        """Width for the wires."""
        width = 0.0
        for seg in self._segments:
            width = max(width, seg.wire_width)
        return width

    @property
    def margin_before(self) -> float:
        """Margin before the lines."""
        margin = 0.0
        for seg in self._segments:
            margin = max(margin, seg.margin_before)
        return margin

    @property
    def margin_after(self) -> float:
        """Margin after the lines."""
        margin = 0.0
        for seg in self._segments:
            margin = max(margin, seg.margin_after)
        return margin

    @property
    def cmin(self) -> Variable:
        """Minimum coordinate along the lane."""
        return self._cmin

    @property
    def cref(self) -> Variable:
        """Reference coordinate along the lane."""
        return self._cref

    @property
    def cmax(self) -> Variable:
        """Maximum coordinate along the lane."""
        return self._cmax
