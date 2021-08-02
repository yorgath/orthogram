"""Provides classes for arranging diagram connections."""

from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
)

from cassowary import Variable  # type: ignore
from cassowary.expression import Constraint  # type: ignore

from shapely.geometry import LineString  # type: ignore

from ..arrange import (
    Joint,
    Wire,
    WireSegment,
)

from ..define import (
    Connection,
    ConnectionAttributes,
)

from ..geometry import (
    Axis,
    Direction,
)

from ..util import class_str

from .functions import arrow_width
from .labels import Label

######################################################################

class DrawingWireLabel:
    """Label on a drawing wire."""

    def __init__(
            self,
            layout_segment: WireSegment, label: Label,
            track_cmin: Variable, track_cmax: Variable
    ):
        """Initialize for the given drawing label."""
        self._drawing_label = label
        self._lmin = track_cmin
        self._lmax = track_cmax
        self._name = layout_segment.name

    def __repr__(self) -> str:
        """Represent as string."""
        name = self._name
        text = repr(self._drawing_label.text)
        content = f"{name}, {text}"
        return class_str(self, content)

    @property
    def drawing_label(self) -> Label:
        """The label to draw on the diagram."""
        return self._drawing_label

    @property
    def lmin(self) -> Variable:
        """Minimum coordinate along the segment."""
        return self._lmin

    @property
    def lmax(self) -> Variable:
        """Maximum coordinate along the segment."""
        return self._lmax

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the label."""
        label = self._drawing_label
        dist = label.attributes.label_distance
        yield self._lmax - self._lmin >= label.length + 2 * dist

######################################################################

class DrawingJoint:
    """Augments a layout joint."""

    def __init__(self, layout_joint: Joint):
        """Initialize for the given layout joint."""
        self._layout_joint = layout_joint
        # Define default coordinate variables.  These may be replaced
        # later on from the segments.
        name = layout_joint.name
        self._x = Variable(f"joint_{name}_x")
        self._y = Variable(f"joint_{name}_y")

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._layout_joint.description()
        return class_str(self, content)

    @property
    def layout_joint(self) -> Joint:
        """The layout joint that corresponds to this drawing object."""
        return self._layout_joint

    @property
    def x(self) -> Variable:
        """Coordinate along the horizontal axis."""
        return self._x

    @x.setter
    def x(self, var: Variable) -> None:
        """Set the variable."""
        self._x = var

    @property
    def y(self) -> Variable:
        """Coordinate along the vertical axis."""
        return self._y

    @y.setter
    def y(self, var: Variable) -> None:
        """Set the variable."""
        self._y = var

######################################################################

class DrawingWireSegment:
    """Augments a layout wire segment."""

    def __init__(
            self,
            layout_segment: WireSegment,
            connection_distance: float,
            start: DrawingJoint, end: DrawingJoint,
            is_first: bool, is_last: bool,
    ):
        """Initialize for the given layout segment."""
        self._layout_segment = layout_segment
        self._connection_distance = connection_distance
        self._start = start
        self._end = end
        self._is_first = is_first
        self._is_last = is_last
        self._wire_width = self._calculate_wire_width()
        self._arrow_margin = self._calculate_arrow_margin()
        # Variables for the constraint solver.
        name = layout_segment.name
        coord_along = "x"
        coord_across = "y"
        if self.is_vertical():
            coord_along, coord_across = coord_across, coord_along
        self._cmin = Variable(f"seg_{name}_{coord_across}min")
        self._cmax = Variable(f"seg_{name}_{coord_across}max")
        # This will be set later using the layers.
        self._cref: Variable
        # These will be set later during the process.
        self._label: Optional[DrawingWireLabel] = None
        self._label_margin = 0.0

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._layout_segment.description()
        return class_str(self, content)

    @property
    def layout_segment(self) -> WireSegment:
        """The layout wire segment wrapped by this object."""
        return self._layout_segment

    def is_horizontal(self) -> bool:
        """True if the segment is horizontal."""
        return self._layout_segment.is_horizontal()

    def is_vertical(self) -> bool:
        """True if the segment is vertical."""
        return not self.is_horizontal()

    @property
    def connection(self) -> Connection:
        """Connection associated with the wire."""
        return self._layout_segment.connection

    @property
    def start(self) -> DrawingJoint:
        """First joint of the segment."""
        return self._start

    @property
    def end(self) -> DrawingJoint:
        """Second joint of the segment."""
        return self._end

    @property
    def direction(self) -> Direction:
        """Direction of the segment."""
        return self._layout_segment.direction

    @property
    def cmin(self) -> Variable:
        """Minimum coordinate perpendicular to the axis."""
        return self._cmin

    @property
    def cref(self) -> Variable:
        """Coordinate of the axis."""
        return self._cref

    @cref.setter
    def cref(self, var: Variable) -> None:
        """Set the variable.

        This updates the variables in the joints as well.

        """
        self._cref = var
        if self.is_horizontal():
            self._start.y = var
            self._end.y = var
        else:
            self._start.x = var
            self._end.x = var

    @property
    def cmax(self) -> Variable:
        """Maximum coordinate perpendicular to the axis."""
        return self._cmax

    @property
    def attributes(self) -> ConnectionAttributes:
        """Attributes of the underlying connection."""
        return self._layout_segment.connection.attributes

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
        self._label_margin = self._calculate_label_margin()

    @property
    def label_displacement(self) -> Tuple[float, float]:
        """Vector from middle of segment to center of label."""
        width = self._wire_width
        disp = -0.5 * (width + self._label_margin)
        if self.is_horizontal():
            return (0.0, disp)
        return (disp, 0.0)

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the segment."""
        yield from self._label_constraints()
        yield from self._across_constraints()

    def _calculate_wire_width(self) -> float:
        """Calculate the width of the wire itself, including buffer."""
        attrs = self.attributes
        width = attrs.stroke_width
        buffer_width = attrs.buffer_width
        if buffer_width:
            width += 2 * buffer_width
        return width

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

    def _calculate_arrow_margin(self) -> float:
        """Calculate a margin large enough for half an arrow.

        This is zero if the connection has neither forward nor
        backward arrow.

        """
        attrs = self.attributes
        if (
                (attrs.arrow_forward and self._is_last) or
                (attrs.arrow_back and self._is_first)
        ):
            # Do not return margin if the distance between lines is
            # sufficient.
            margin = 0.5 * (arrow_width(attrs) - self._connection_distance)
            return max(margin, 0.0)
        return 0.0

    def _label_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the labels."""
        wire_label = self._label
        if wire_label:
            yield from wire_label.constraints()

    def _across_constraints(self) -> Iterator[Constraint]:
        """Generate constraints across the segment."""
        yield from self._orientation_constraints()
        yield from self._width_constraints()

    def _orientation_constraints(self) -> Iterator[Constraint]:
        """Generate constraints according to the orientation."""
        if self.is_horizontal():
            yield self._start.y == self._end.y
        else:
            yield self._start.x == self._end.x

    def _width_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the width of the occupied area."""
        # Must contain the arrows and the label.
        arrow_margin = self._arrow_margin
        line_half_width = 0.5 * self._wire_width
        label_margin = self._label_margin
        before = max(arrow_margin, line_half_width + label_margin)
        after = max(arrow_margin, line_half_width)
        yield self._cref - self._cmin >= before
        yield self._cmax - self._cref >= after

######################################################################

class DrawingWire:
    """Augments a layout wire."""

    def __init__(self, layout_wire: Wire) -> None:
        """Initialize an empty wire."""
        self._layout_wire = layout_wire
        self._segments: List[DrawingWireSegment] = []

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._layout_wire.description()
        return class_str(self, content)

    @property
    def layout_wire(self) -> Wire:
        """The layout wire wrapped by this object."""
        return self._layout_wire

    @property
    def connection(self) -> Connection:
        """Associated connection."""
        return self._layout_wire.connection

    def segments(self) -> Iterator[DrawingWireSegment]:
        """Iterate over the segments that make up this wire."""
        yield from self._segments

    @property
    def line_string(self) -> LineString:
        """Return a line string for drawing the connection."""
        points: List[Tuple[float, float]] = []
        for seg in self._segments:
            if not points:
                joint_1 = seg.start
                point_1 = (joint_1.x.value, joint_1.y.value)
                points.append(point_1)
            joint_2 = seg.end
            point_2 = (joint_2.x.value, joint_2.y.value)
            points.append(point_2)
        return LineString(points)

    def append_segment(self, segment: DrawingWireSegment) -> None:
        """Append segment to the wire."""
        self._segments.append(segment)

######################################################################

class DrawingNetwork:
    """Augments a layout network."""

    def __init__(self, name: str) -> None:
        """Initialize an empty network."""
        self._name = name
        self._wires: List[DrawingWire] = []

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._name)
        return class_str(self, content)

    def append_wire(self, wire: DrawingWire) -> None:
        """Add a wire to the network."""
        self._wires.append(wire)

    def wires(self) -> Iterator[DrawingWire]:
        """Iterate over the wires."""
        yield from self._wires

######################################################################

class DrawingWireLayer:
    """Collection of drawing segments having the same offset."""

    def __init__(self, struct_name: str, offset: int):
        """Initialize an empty layer."""
        self._name = name = f"{struct_name}.{offset}"
        self._offset = offset
        var_name = f"lay_{name}_ref"
        self._cref = Variable(var_name)
        self._segments: List[DrawingWireSegment] = []

    def __repr__(self) -> str:
        """Represent as string."""
        return class_str(self, repr(self._name))

    def __iter__(self) -> Iterator[DrawingWireSegment]:
        """Iterate over the segments."""
        yield from self._segments

    @property
    def offset(self) -> int:
        """Common offset of the segments in the layer."""
        return self._offset

    @property
    def cref(self) -> Variable:
        """Coordinate along the axis."""
        return self._cref

    def append(self, segment: DrawingWireSegment) -> None:
        """Add a segment to the layer."""
        self._segments.append(segment)

######################################################################

class DrawingWireStructure:
    """Collection of overlapping wire segments."""

    def __init__(self, name: str, axis: Axis, connection_distance: float):
        """Initialize an empty structure for the given axis."""
        self._name = name
        self._axis = axis
        self._connection_distance = connection_distance
        self._layers_by_offset: Dict[int, DrawingWireLayer] = {}

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._name)
        return class_str(self, content)

    def __iter__(self) -> Iterator[DrawingWireLayer]:
        """Iterate over the layers by offset in ascending order."""
        by_offset = self._layers_by_offset
        for offset in sorted(by_offset):
            yield by_offset[offset]

    @property
    def axis(self) -> Axis:
        """Axis on which the segments sit."""
        return self._axis

    def add_layer(self, layer: DrawingWireLayer) -> None:
        """Add a layer to the structure."""
        self._layers_by_offset[layer.offset] = layer

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the solver."""
        # Order of segments in the structure.
        dist = self._connection_distance
        layers = list(self)
        for i, lay1 in enumerate(layers[:-1]):
            for seg1 in lay1:
                for lay2 in layers[i + 1:]:
                    for seg2 in lay2:
                        yield seg2.cmin >= seg1.cmax + dist
