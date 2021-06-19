"""Connection network elements for the Refiner."""

from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum, auto

from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import networkx as nx # type: ignore

from ..define import (
    Connection,
    Node,
)

from ..geometry import (
    Axis,
    Direction,
    FloatPoint,
    IntPoint,
    Orientation,
    OrientedVector,
)

from .route import (
    Route,
    RouteSegment,
)

######################################################################

class NetworkOrigin(Enum):
    """Origin of the routes in a network.

    The routes come either from a group or a single route that does
    not belong to any declared group (and is thus placed in a group by
    itself).  Because the name of a route and the name of a group may
    clash (however unlikely), this is used as the first part of the
    key that identifies a network.

    """
    GROUP = auto()
    ROUTE = auto()

######################################################################

class Bundle(OrientedVector):
    """Collection of collinear interacting route segments."""

    def __init__(self, route_segments: Iterable[RouteSegment]):
        """Initialize with the given route segments.

        At least one route segment must be given.  This is necessary
        in order to compute the properties of the bundle.  Empty
        bundles cannot exist.

        """
        seg_list = list(route_segments)
        assert seg_list
        self._route_segments = seg_list
        seg = seg_list[0]
        self._axis = axis = seg.axis
        # Calculate the coordinate range.
        horizontal = axis.orientation is Orientation.HORIZONTAL
        coords = set()
        for seg in seg_list:
            for point in seg.through_points():
                if horizontal:
                    coords.add(point.j)
                else:
                    coords.add(point.i)
        self._coords = min(coords), max(coords)
        # Initialize the offset.
        self._offset = 0

    def __repr__(self) -> str:
        """Convert to string."""
        coords = self._coords
        return "{}({};{}->{})".format(
            self.__class__.__name__,
            self._axis,
            coords[0],
            coords[1],
        )

    @property
    def axis(self) -> Axis:
        """Axis on which the bundle lies."""
        return self._axis

    @property
    def coordinates(self) -> Tuple[int, int]:
        """First and last coordinates along the axis.

        Since the bundle may contain segments with different
        directions, the direction of the bundle itself is always
        either down or to the right.

        """
        return self._coords

    def route_segments(self) -> Iterator[RouteSegment]:
        """Return an iterator over the associated segments."""
        yield from self._route_segments

    @property
    def offset(self) -> int:
        """Offset of the bundle relative to the central axis."""
        return self._offset

    @offset.setter
    def offset(self, value: int) -> None:
        self._offset = value

######################################################################

class Joint:
    """Placed at the ends of segments to combine the offsets."""

    def __init__(
            self,
            point: IntPoint,
            horizontal: Optional[Bundle],
            vertical: Optional[Bundle],
            node: Optional[Node] = None,
    ):
        """Initialize the joint at the meeting point of the two bundles."""
        self._point = point
        self._horizontal_bundle = horizontal
        self._vertical_bundle = vertical
        self._node = node

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}(p={},h={},v={})".format(
            self.__class__.__name__,
            self._point,
            self._horizontal_bundle,
            self._vertical_bundle,
        )

    @property
    def point(self) -> IntPoint:
        """Central point of placement."""
        return self._point

    @property
    def horizontal_offset(self) -> int:
        """Horizontal offset."""
        bundle = self._vertical_bundle
        if bundle:
            return bundle.offset
        return 0

    @property
    def vertical_offset(self) -> int:
        """Vertical offset."""
        bundle = self._horizontal_bundle
        if bundle:
            return bundle.offset
        return 0

    @property
    def node(self) -> Optional[Node]:
        """Node on which the joint lies."""
        return self._node

    @node.setter
    def node(self, node: Node) -> None:
        """Set the node."""
        self._node = node

######################################################################

class WireSegment(OrientedVector):
    """Segment between two angles of a wire."""

    def __init__(self, route_segment: RouteSegment, start: Joint, end: Joint):
        """Initialize the wire."""
        self._route_segment = route_segment
        self._start = start
        self._end = end

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({})".format(
            self.__class__.__name__,
            self._route_segment,
        )

    @property
    def route_segment(self) -> RouteSegment:
        """The route segment associated with this wire segment."""
        return self._route_segment

    @property
    def connection(self) -> Connection:
        """Connection behind the wire."""
        return self._route_segment.connection

    @property
    def axis(self) -> Axis:
        """Axis on which the segment lies."""
        return self._route_segment.axis

    @property
    def coordinates(self) -> Tuple[int, int]:
        """First and last coordinates along the axis."""
        return self._route_segment.coordinates

    @property
    def offset(self) -> int:
        """Offset relative to the central axis."""
        joint = self._start
        if self._route_segment.is_horizontal():
            return joint.vertical_offset
        return joint.horizontal_offset

    @property
    def start(self) -> Joint:
        """First joint of the segment."""
        return self._start

    @property
    def end(self) -> Joint:
        """Second joint of the segment."""
        return self._end

    @property
    def joints(self) -> Tuple[Joint, Joint]:
        """The joints at the two ends of the segment."""
        return self._start, self._end

    @property
    def label_orientation(self) -> Orientation:
        """Orientation of the label, horizontal of vertical.

        See RouteSegment property of the same name.

        """
        return self._route_segment.label_orientation

    def cut_by(self, other: 'WireSegment') -> Optional[int]:
        """Return the coordinate the other segment cuts this."""
        ori_self = self.orientation
        ori_other = other.orientation
        if ori_other is ori_self:
            # Parallel segments do not interset.
            return None
        min_self, max_self = self.min_max_coordinates
        base_other = other.axis.coordinate
        if base_other <= min_self or base_other >= max_self:
            return None
        base_self = self.axis.coordinate
        off_self = self.offset
        min_other, max_other = other.min_max_coordinates
        dir_other = other.direction
        if dir_other is Direction.DOWN:
            off_1_other = other.start.vertical_offset
            off_2_other = other.end.vertical_offset
        elif dir_other is Direction.LEFT:
            off_1_other = other.end.horizontal_offset
            off_2_other = other.start.horizontal_offset
        elif dir_other is Direction.RIGHT:
            off_1_other = other.start.horizontal_offset
            off_2_other = other.end.horizontal_offset
        if dir_other is Direction.UP:
            off_1_other = other.end.vertical_offset
            off_2_other = other.start.vertical_offset
        if max_other < base_self:
            # Other is above/left.  No cut.
            return None
        if max_other == base_self:
            # Touches from above/left.
            if off_2_other >= off_self:
                return base_other
            return None
        if min_other < base_self:
            # Obvious intersection.
            return base_other
        if min_other == base_self:
            # Touches from below/right.
            if off_1_other < off_self:
                return base_other
            return None
        # Other is below/right.  No cut.
        return None

######################################################################

class Wire:
    """Connects two blocks together."""

    def __init__(self, route: Route, segments: Sequence[WireSegment]):
        """Create a wire with the given segments for a route."""
        self._route = route
        self._segments = list(segments)

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({})".format(
            self.__class__.__name__,
            self._route.name,
        )

    def segments(self) -> Iterator[WireSegment]:
        """Return an iterator over the segments."""
        yield from self._segments

    @property
    def connection(self) -> Connection:
        """Associated connection."""
        return self._route.connection

######################################################################

class Network:
    """Collection of routes that belong to the same group."""

    def __init__(
            self,
            origin: NetworkOrigin,
            group: str,
            routes: Iterable[Route]
    ):
        """Initialize with the given routes."""
        self._origin = origin
        self._group = group
        self._routes = list(routes)
        self._bundles: List[Bundle] = []
        self._init_bundles()
        self._joints: MutableMapping[IntPoint, Joint] = OrderedDict()
        self._init_joints()
        self._wires: List[Wire] = []
        self._init_wires()

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({},{};routes={};bundles={})".format(
            self.__class__.__name__,
            self._origin.name,
            self._group,
            len(self._routes),
            len(self._bundles),
        )

    def bundles(self) -> Iterator[Bundle]:
        """Return an iterator over the bundles of the network."""
        yield from self._bundles

    def wires(self) -> Iterator[Wire]:
        """Return an iterator over the calculated wires."""
        yield from self._wires

    def joints(self) -> Iterator[Joint]:
        """Return an iterator over all the joints of the network."""
        yield from self._joints.values()

    def offset_bundle(self, bundle: Bundle, use_offsets: bool) -> Tuple[FloatPoint, FloatPoint]:
        """Return a pair of points suitable for overlap check."""
        joint_1 = self._joints[bundle.first_point]
        point_1 = self._float_point(bundle, joint_1, use_offsets)
        joint_2 = self._joints[bundle.last_point]
        point_2 = self._float_point(bundle, joint_2, use_offsets)
        return point_1, point_2

    def _init_bundles(self) -> None:
        """Create the bundles of segments."""
        # Use a graph to discover the interactions.
        graph = nx.Graph()
        segments = []
        for route in self._routes:
            for seg in route.segments():
                segments.append(seg)
                graph.add_node(seg)
        n_segments = len(segments)
        for i in range(n_segments):
            seg1 = segments[i]
            for j in range(i + 1, n_segments):
                seg2 = segments[j]
                if self._segments_interact(seg1, seg2):
                    graph.add_edge(seg1, seg2)
        bundles = self._bundles
        bundles.clear()
        done = set()
        for segments in nx.connected_components(graph):
            bundle_segments = []
            for seg in segments:
                bundle_segments.append(seg)
                done.add(seg)
            bundle = Bundle(bundle_segments)
            bundles.append(bundle)

    @staticmethod
    def _segments_interact(
            segment_1: RouteSegment,
            segment_2: RouteSegment
    ) -> bool:
        """True if the segments are collinear and share points."""
        if segment_1 is segment_2:
            return False
        if segment_1.axis != segment_2.axis:
            return False
        points_1 = set(segment_1.through_points())
        points_2 = set(segment_2.through_points())
        for _ in points_1.intersection(points_2):
            return True
        return False

    def _init_joints(self) -> None:
        """Create the joints."""
        # Find the bundles at each point.
        horizontal: MutableMapping[IntPoint, Bundle] = OrderedDict()
        vertical: MutableMapping[IntPoint, Bundle] = OrderedDict()
        self._collect_bundles(horizontal, vertical)
        # Create the joints at each segment end.
        joints = self._joints
        joints.clear()
        for route in self._routes:
            for seg in route.segments():
                points = [seg.first_point, seg.last_point]
                for point in points:
                    if point not in joints:
                        hor = horizontal.get(point)
                        ver = vertical.get(point)
                        joint = Joint(point, hor, ver)
                        joints[point] = joint

    def _collect_bundles(
            self,
            horizontal: MutableMapping[IntPoint, Bundle],
            vertical: MutableMapping[IntPoint, Bundle],
    ) -> None:
        """Collect the bundles at each point in the given collections."""
        collections = {
            Orientation.HORIZONTAL: horizontal,
            Orientation.VERTICAL: vertical,
        }
        for bundle in self._bundles:
            ori = bundle.orientation
            col = collections[ori]
            for point in bundle.through_points():
                col[point] = bundle

    def _init_wires(self) -> None:
        """Create the wires."""
        wires = self._wires
        wires.clear()
        joints = self._joints
        for route in self._routes:
            segments = []
            for rseg in route.segments():
                joint_1 = joints[rseg.first_point]
                joint_2 = joints[rseg.last_point]
                cseg = WireSegment(rseg, joint_1, joint_2)
                segments.append(cseg)
            wire = Wire(route, segments)
            wires.append(wire)

    # In order to find bundles that overlap, the integer offsets are
    # converted to real numbers by multiplying with this quantity.
    _FACTOR = 0.001

    @classmethod
    def _float_point(
            cls,
            bundle: Bundle, joint: Joint,
            use_offsets: bool,
    ) -> FloatPoint:
        """Calculate coordinates for the joint to be used in overlap checks."""
        point = joint.point
        factor = cls._FACTOR
        # If there is a node at the joint, move the point a bit to
        # avoid false positives.
        if joint.node:
            ori = bundle.orientation
            out = (point == bundle.first_point)
            key = (ori, out)
            values = {
                (Orientation.VERTICAL, False): (0, -1),
                (Orientation.VERTICAL, True): (0, 1),
                (Orientation.HORIZONTAL, False): (-1, 0),
                (Orientation.HORIZONTAL, True): (1, 0),
            }
            diffs = values[key]
        else:
            diffs = (0, 0)
        point_x = point.j + factor * diffs[0]
        point_y = point.i + factor * diffs[1]
        if use_offsets:
            point_x += factor * joint.horizontal_offset
            point_y += factor * joint.vertical_offset
        return FloatPoint(point_x, point_y)

######################################################################

@dataclass(frozen=True)
class NetworkBundle:
    """Combination of a network and one of its bundles."""
    network: Network
    bundle: Bundle

    def overlaps_with(self, other: 'NetworkBundle', use_offsets: bool) -> bool:
        """True if this bundle overlaps with the given one."""
        net1, bundle1 = self.network, self.bundle
        net2, bundle2 = other.network, other.bundle
        if bundle1.axis != bundle2.axis:
            return False
        p11, p12 = net1.offset_bundle(bundle1, use_offsets)
        p21, p22 = net2.offset_bundle(bundle2, use_offsets)
        horizontal = bundle1.orientation is Orientation.HORIZONTAL
        vertical = not horizontal
        if horizontal and p11.x <= p22.x and p12.x >= p21.x:
            return True
        if vertical and p11.y <= p22.y and p12.y >= p21.y:
            return True
        return False

######################################################################

class BundleLayer:
    """Collection of bundles having the same offset."""

    def __init__(self, offset: int):
        """Initialize an empty layer."""
        self._offset = offset
        self._net_bundles: List[NetworkBundle] = []

    def append(self, net_bundle: NetworkBundle) -> None:
        """Add a network bundle to the layer."""
        self._net_bundles.append(net_bundle)

    @property
    def offset(self) -> int:
        """Common offset of the bundles in the layer."""
        return self._offset

    def __iter__(self) -> Iterator[NetworkBundle]:
        """Yield the network bundles (in no particular order)."""
        yield from self._net_bundles

######################################################################

class BundleStructure:
    """Collection of overlapping bundles."""

    def __init__(self, axis: Axis, net_bundles: Iterable[NetworkBundle]):
        """Initialize for the given bundles."""
        self._axis = axis
        self._layers_by_offset = self._make_layers(net_bundles)

    @staticmethod
    def _make_layers(
            net_bundles: Iterable[NetworkBundle]
    ) -> MutableMapping[int, BundleLayer]:
        """Group bundles into layers by offset."""
        result: Dict[int, BundleLayer] = {}
        for net_bundle in net_bundles:
            offset = net_bundle.bundle.offset
            if offset not in result:
                result[offset] = BundleLayer(offset)
            result[offset].append(net_bundle)
        return result

    def optimize(self) -> None:
        """Pack bundles as densely as possible.

        This method recreates the layers of the structure and updates
        the offsets stored in the bundles.

        """
        # Recreate layers.
        layers = self._pack_bundles()
        by_offset = self._layers_by_offset
        by_offset.clear()
        for layer in layers:
            by_offset[layer.offset] = layer
        # Store the minimized offsets.
        for i, net_bundles in enumerate(layers):
            for net_bundle in net_bundles:
                net_bundle.bundle.offset = i

    def _pack_bundles(self) -> Sequence[BundleLayer]:
        """Return a dense arrangement of the existing bundle layers."""
        layers: List[BundleLayer] = []
        for net_bundle in self.network_bundles():
            overlap_on = -1
            n_layers = len(layers)
            for i in range(n_layers - 1, -1, -1):
                layer = layers[i]
                for net_bundle_2 in layer:
                    if net_bundle.overlaps_with(net_bundle_2, True):
                        overlap_on = i
                        break
                if overlap_on >= 0:
                    break
            if overlap_on == n_layers - 1:
                # New layer.
                layer = BundleLayer(overlap_on + 1)
                layer.append(net_bundle)
                layers.append(layer)
            else:
                # Append to existing layer.
                layers[overlap_on + 1].append(net_bundle)
        return layers

    @property
    def axis(self) -> Axis:
        """Axis on which the bundles sit."""
        return self._axis

    def __iter__(self) -> Iterator[BundleLayer]:
        """Iterate over the layer in offset order."""
        by_offset = self._layers_by_offset
        for offset in sorted(by_offset):
            yield by_offset[offset]

    def network_bundles(self) -> Iterator[NetworkBundle]:
        """Iterate over the elements in offset order."""
        for layer in self:
            yield from layer
