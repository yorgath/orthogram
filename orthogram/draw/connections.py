"""Provides classes for arranging diagram connections."""

from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
)

from cassowary import Variable  # type: ignore

from cassowary.expression import (  # type: ignore
    Constraint,
    Expression,
)

from shapely.geometry import LineString  # type: ignore

from ..arrange import (
    Joint,
    Wire,
    WireSegment,
)

from ..define import (
    ConnectionAttributes,
    ConnectionLabelPosition,
)

from ..geometry import (
    Axis,
    OrientedVector,
)

from ..util import class_str

from .functions import (
    arrow_width,
    wire_width,
)

from .labels import DrawingWireLabel

######################################################################

class DrawingJoint:
    """Augments a layout joint."""

    def __init__(self, layout_joint: Joint):
        """Initialize for the given layout joint."""
        self._layout_joint = layout_joint
        # These will be set later from the blocks and segments.
        self._x: Variable
        self._y: Variable

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
        self._wire_width = wire_width(layout_segment.connection.attributes)
        # Labels may be set later during the process.
        self._start_label: Optional[DrawingWireLabel] = None
        self._middle_label: Optional[DrawingWireLabel] = None
        self._end_label: Optional[DrawingWireLabel] = None
        # These will be set later from the layers.
        self._cref: Variable
        self._cmin: Expression
        self._cmax: Expression

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._layout_segment.description()
        return class_str(self, content)

    @property
    def layout_segment(self) -> WireSegment:
        """The layout wire segment wrapped by this object."""
        return self._layout_segment

    @property
    def grid_vector(self) -> OrientedVector:
        """Vector of the segment in grid space."""
        return self._layout_segment.grid_vector

    @property
    def start(self) -> DrawingJoint:
        """First joint of the segment."""
        return self._start

    @property
    def end(self) -> DrawingJoint:
        """Second joint of the segment."""
        return self._end

    @property
    def attributes(self) -> ConnectionAttributes:
        """Attributes of the underlying connection."""
        return self._layout_segment.connection.attributes

    @property
    def wire_width(self) -> float:
        """Width of the connection wire."""
        return self._wire_width

    def labels(self) -> Iterator[DrawingWireLabel]:
        """Iterate over the labels attached to the segment."""
        labels = [
            self._start_label,
            self._middle_label,
            self._end_label,
        ]
        for label in labels:
            if label:
                yield label

    def add_label(self, label: DrawingWireLabel) -> None:
        """Add the label at the appropriate position."""
        position = label.position
        if position is ConnectionLabelPosition.START:
            self._start_label = label
        elif position is ConnectionLabelPosition.END:
            self._end_label = label
        else:
            self._middle_label = label
        # After adding labels the dimensions may have to change.
        self._update_dimensions()

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

        This updates the coverage of the segment and the variables in
        the joints.

        """
        self._cref = var
        self._update_dimensions()
        if self.grid_vector.is_horizontal():
            self._start.y = var
            self._end.y = var
        else:
            self._start.x = var
            self._end.x = var

    @property
    def cmax(self) -> Variable:
        """Maximum coordinate perpendicular to the axis."""
        return self._cmax

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the segment."""
        yield from self._label_constraints()

    def _label_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the labels."""
        for label in self.labels():
            yield from label.constraints()

    def _update_dimensions(self) -> None:
        """Recalculate the distances relative to the reference line."""
        self._cmin = self._cref - self._height_before()
        self._cmax = self._cref + self._height_after()

    def _height_before(self) -> float:
        """Distance from minimum coordinate to reference line."""
        height = self._height_with_arrows()
        dist = self._connection_distance
        for label in self.labels():
            height = max(height, label.perpendicular_coverage() + dist)
        return height

    def _height_after(self) -> float:
        """Distance from reference line to maximum coordinate."""
        return self._height_with_arrows()

    def _height_with_arrows(self) -> float:
        """Distance from reference line to arrow base included."""
        line_half_height = 0.5 * self._wire_width
        distance = self._connection_distance
        half_distance = 0.5 * distance
        min_half_height = line_half_height + half_distance
        arrow_half_height = 0.5 * self._height_for_arrows()
        return max(min_half_height, arrow_half_height)

    def _height_for_arrows(self) -> float:
        """Height necessary to contain the arrows of the segment."""
        attrs = self.attributes
        if (
                (attrs.arrow_forward and self._is_last) or
                (attrs.arrow_back and self._is_first)
        ):
            return arrow_width(attrs)
        return 0.0

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

    def __iter__(self) -> Iterator[DrawingWireSegment]:
        """Iterate over the segments that make up this wire."""
        yield from self._segments

    @property
    def layout_wire(self) -> Wire:
        """The layout wire wrapped by this object."""
        return self._layout_wire

    def append(self, segment: DrawingWireSegment) -> None:
        """Append segment to the wire."""
        self._segments.append(segment)

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

    def __iter__(self) -> Iterator[DrawingWire]:
        """Iterate over the wires."""
        yield from self._wires

    def append(self, wire: DrawingWire) -> None:
        """Add a wire to the network."""
        self._wires.append(wire)

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
        """Coordinate perpendicular to the axis."""
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

    def add(self, layer: DrawingWireLayer) -> None:
        """Add a layer to the structure."""
        self._layers_by_offset[layer.offset] = layer

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the solver."""
        # Order of segments in the structure.
        layers = list(self)
        for i, lay1 in enumerate(layers[:-1]):
            for seg1 in lay1:
                for lay2 in layers[i + 1:]:
                    for seg2 in lay2:
                        yield seg2.cmin >= seg1.cmax
