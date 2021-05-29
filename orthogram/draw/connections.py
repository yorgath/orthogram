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

from ..geometry import Axis
from ..util import class_str

from .labels import Label

######################################################################

class DrawingWireLabel:
    """Label on a drawing wire."""

    def __init__(self, label: Label, cmin: Variable, cmax: Variable):
        """Initialize for the given drawing label."""
        self._drawing_label = label
        self._cmin = cmin
        self._cmax = cmax

    def __repr__(self) -> str:
        """Represent as string."""
        text = repr(self._drawing_label.text)
        return class_str(self, text)

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
    ):
        """Initialize for the given layout segment."""
        self._layout_segment = layout_segment
        self._connection_distance = connection_distance
        self._start = start
        self._end = end
        self._wire_width = self._calculate_wire_width()
        # Variables for the constraint solver.
        name = layout_segment.name
        if self.is_horizontal():
            coord_name = "y"
        else:
            coord_name = "x"
        self._cmin = Variable(f"seg_{name}_{coord_name}min")
        self._cmax = Variable(f"seg_{name}_{coord_name}max")
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
    def cmin(self) -> Variable:
        """Minimum coordinate along the axis."""
        return self._cmin

    @property
    def cref(self) -> Variable:
        """Coordinate along the axis."""
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
        """Maximum coordinate along the axis."""
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
        yield from self._joint_constraints()
        yield from self._bounds_constraints()

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

    def _joint_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the joints at the two ends."""
        start = self._start
        end = self._end
        if self.is_horizontal():
            yield start.y == end.y
        else:
            yield start.x == end.x

    def _bounds_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for bounds of the segment."""
        half_width = 0.5 * self._wire_width
        yield self._cmin <= self._cref - half_width - self._label_margin
        yield self._cmax >= self._cref + half_width

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
