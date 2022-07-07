"""Connection network elements for the Refiner."""

from enum import Enum, auto

from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    MutableMapping,
    Optional,
    Tuple,
)

import networkx as nx  # type: ignore

from ..define import (
    Connection,
    Node,
    Side,
)

from ..geometry import (
    Axis,
    Direction,
    FloatPoint,
    IntPoint,
    Orientation,
    OrientedVector,
)

from ..util import (
    class_str,
    indent,
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

class Bundle:
    """Collection of collinear interacting route segments."""

    def __init__(
            self,
            name: str,
            route_segments: Iterable[RouteSegment],
    ):
        """Initialize with the given route segments.

        At least one route segment must be given.  This is necessary
        in order to compute the properties of the bundle.  Empty
        bundles cannot exist.

        """
        self._name = name
        seg_list = list(route_segments)
        assert seg_list
        self._route_segments = seg_list
        a_segment = seg_list[0]
        bundle_axis = a_segment.grid_vector.axis
        # Calculate the coordinate range.
        horizontal = bundle_axis.is_horizontal()
        coords = set()
        for seg in seg_list:
            vec = seg.grid_vector
            # All segments must be collinear.
            assert vec.axis == bundle_axis
            for point in vec.through_points():
                if horizontal:
                    coords.add(point.j)
                else:
                    coords.add(point.i)
        # Bundle is always top-to-bottom or left-to-right.
        coord_pair = min(coords), max(coords)
        self._grid_vector = OrientedVector(bundle_axis, coord_pair)
        # This is what we must calculate.
        self._offset = 0

    def __repr__(self) -> str:
        """Represent as string."""
        desc = self.description()
        offset = self.offset
        content =  f"{desc}, offset={offset}"
        return class_str(self, content)

    def route_segments(self) -> Iterator[RouteSegment]:
        """Iterate over the associated segments."""
        yield from self._route_segments

    @property
    def grid_vector(self) -> OrientedVector:
        """Vector between the two ends of the bundle on the grid."""
        return self._grid_vector

    @property
    def offset(self) -> int:
        """Offset of the bundle relative to the central axis."""
        return self._offset

    @offset.setter
    def offset(self, value: int) -> None:
        """Set the offset."""
        self._offset = value

    def description(self) -> str:
        """Return a description of the bundle."""
        name = repr(self._name)
        points = self._grid_vector.vector_depiction()
        return f"{name}, points={points}"

    def _pretty_print(self, level: int = 0) -> None:
        """Print the object for debugging purposes."""
        print(indent(level) + repr(self))
        for segment in self.route_segments():
            print(indent(level + 1) + repr(segment))

######################################################################

class Joint:
    """Placed at the ends of segments to combine the offsets."""

    def __init__(
            self,
            name: str,
            point: IntPoint,
            horizontal: Optional[Bundle],
            vertical: Optional[Bundle],
            node: Optional[Node] = None,
    ):
        """Initialize the joint at the meeting point of the two bundles."""
        self._name = name
        self._point = point
        self._horizontal_bundle = horizontal
        self._vertical_bundle = vertical
        self._node = node

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def point(self) -> IntPoint:
        """Grid point around which the joint is placed."""
        return self._point

    @property
    def node(self) -> Optional[Node]:
        """Node on which the joint lies."""
        return self._node

    @node.setter
    def node(self, node: Node) -> None:
        """Set the node."""
        self._node = node

    @property
    def horizontal_offset(self) -> int:
        """Horizontal offset relative to the point."""
        bundle = self._vertical_bundle
        if bundle:
            return bundle.offset
        return 0

    @property
    def vertical_offset(self) -> int:
        """Vertical offset relative to the point."""
        bundle = self._horizontal_bundle
        if bundle:
            return bundle.offset
        return 0

    @property
    def name(self) -> str:
        """Name of the joint."""
        return self._name

    def description(self) -> str:
        """Return a description of the joint."""
        name = repr(self._name)
        point = self._point
        i, j = point.i, point.j
        return f"{name}, i={i}, j={j}"

######################################################################

class WireSegment:
    """Segment between two angles of a wire."""

    def __init__(
            self,
            route_segment: RouteSegment,
            start: Joint, end: Joint,
            is_first: bool, is_last: bool,
    ):
        """Initialize for the given route segment."""
        self._route_segment = route_segment
        self._start = start
        self._end = end
        self._is_first = is_first
        self._is_last = is_last

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def route_segment(self) -> RouteSegment:
        """The route segment associated with this wire segment."""
        return self._route_segment

    @property
    def index(self) -> int:
        """Index number of the segment along the wire."""
        return self._route_segment.index

    @property
    def connection(self) -> Connection:
        """Connection associated with the wire."""
        return self._route_segment.connection

    @property
    def grid_vector(self) -> OrientedVector:
        """Vector of the segment in grid space."""
        return self._route_segment.grid_vector

    @property
    def joints(self) -> Tuple[Joint, Joint]:
        """The joints at the two ends of the segment."""
        return self._start, self._end

    @property
    def start(self) -> Joint:
        """First joint of the segment."""
        return self._start

    @property
    def end(self) -> Joint:
        """Second joint of the segment."""
        return self._end

    def is_first(self) -> bool:
        """True if this is the first segment of the wire."""
        return self._is_first

    def is_last(self) -> bool:
        """True if this is the last segment of the wire."""
        return self._is_last

    @property
    def offset(self) -> int:
        """Offset relative to the central axis."""
        joint = self._start
        if self.grid_vector.is_horizontal():
            return joint.vertical_offset
        return joint.horizontal_offset

    @property
    def name(self) -> str:
        """Name of the segment."""
        return self._route_segment.name

    def description(self) -> str:
        """Return a description of the wire segment."""
        return self._route_segment.description()

    def cut_by(self, other: 'WireSegment') -> Optional[int]:
        """Return the coordinate at which the other segment cuts this."""
        vec_self = self.grid_vector
        axis_self = vec_self.axis
        ori_self = axis_self.orientation
        vec_other = other.grid_vector
        axis_other = vec_other.axis
        ori_other = axis_other.orientation
        if ori_other is ori_self:
            # Parallel segments do not interset.
            return None
        min_self, max_self = vec_self.min_max_coordinates
        base_other = axis_other.coordinate
        if base_other <= min_self or base_other >= max_self:
            return None
        base_self = axis_self.coordinate
        off_self = self.offset
        min_other, max_other = vec_other.min_max_coordinates
        dir_other = vec_other.direction
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

    def __init__(
            self,
            route: Route,
            segments: Iterable[WireSegment],
    ):
        """Create a wire with the given segments for a route."""
        self._route = route
        self._segments = segments = list(segments)
        # Must have at least one segment.
        assert segments

    def __getitem__(self, i: int) -> WireSegment:
        """Return the i-th segment."""
        return self._segments[i]

    def __iter__(self) -> Iterator[WireSegment]:
        """Iterate over the segments."""
        yield from self._segments

    def __len__(self) -> int:
        """Return the number of segments."""
        return len(self._segments)

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def connection(self) -> Connection:
        """Associated connection."""
        return self._route.connection

    def description(self) -> str:
        """Return a description of the wire."""
        return self._route.description()

    def attachment_sides(self) -> Tuple[Side, Side]:
        """Sides of the blocks to which the wire is attached."""
        first = self[0]
        first_dir = first.grid_vector.direction
        if first_dir is Direction.DOWN:
            first_side = Side.BOTTOM
        elif first_dir is Direction.LEFT:
            first_side = Side.LEFT
        elif first_dir is Direction.RIGHT:
            first_side = Side.RIGHT
        elif first_dir is Direction.UP:
            first_side = Side.TOP
        last = self[-1]
        last_dir = last.grid_vector.direction
        if last_dir is Direction.DOWN:
            last_side = Side.TOP
        elif last_dir is Direction.LEFT:
            last_side = Side.RIGHT
        elif last_dir is Direction.RIGHT:
            last_side = Side.LEFT
        elif last_dir is Direction.UP:
            last_side = Side.BOTTOM
        return first_side, last_side

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
        self._name = f"{origin.name}_{group}"
        self._bundles = self._make_bundles()
        self._joints = self._make_joints()
        self._joint_map = self._map_points_to_joints()
        self._wires = self._make_wires()

    def __repr__(self) -> str:
        """Represent as string."""
        return class_str(self, repr(self._name))

    @property
    def name(self) -> str:
        """Name of the network."""
        return self._name

    def bundles(self) -> Iterator[Bundle]:
        """Iterate over the bundles that make up the network."""
        yield from self._bundles

    def wires(self) -> Iterator[Wire]:
        """Iterate over the calculated wires."""
        yield from self._wires

    def joints(self) -> Iterator[Joint]:
        """Iterate over all the joints of the network."""
        yield from self._joints

    def offset_bundle(
            self, bundle: Bundle, use_offsets: bool
    ) -> Tuple[FloatPoint, FloatPoint]:
        """Return a pair of points suitable for overlap check."""
        jmap = self._joint_map
        vec = bundle.grid_vector
        joint_1 = jmap[vec.first_point]
        point_1 = self._float_point(bundle, joint_1, use_offsets)
        joint_2 = jmap[vec.last_point]
        point_2 = self._float_point(bundle, joint_2, use_offsets)
        return point_1, point_2

    def _make_bundles(self) -> List[Bundle]:
        """Create the bundles of segments."""
        # Use a graph to discover the interactions.
        graph = nx.Graph()
        segments = []
        for route in self._routes:
            for seg in route:
                segments.append(seg)
                graph.add_node(seg)
        n_segments = len(segments)
        for i in range(n_segments):
            seg1 = segments[i]
            for j in range(i + 1, n_segments):
                seg2 = segments[j]
                if self._segments_interact(seg1, seg2):
                    graph.add_edge(seg1, seg2)
        bundles: List[Bundle] = []
        net_name = str(self._name)
        for segments in nx.connected_components(graph):
            index = len(bundles)
            name = f"{net_name}.{index}"
            bundle = Bundle(name, segments)
            bundles.append(bundle)
        return bundles

    @staticmethod
    def _segments_interact(
            segment_1: RouteSegment,
            segment_2: RouteSegment
    ) -> bool:
        """True if the segments are collinear and share points.

        This is defined here instead on the route segment class,
        because it is a very particular implementation.

        """
        if segment_1 is segment_2:
            return False
        if segment_1.grid_vector.axis != segment_2.grid_vector.axis:
            return False
        points_1 = set(segment_1.grid_vector.through_points())
        points_2 = set(segment_2.grid_vector.through_points())
        for _ in points_1.intersection(points_2):
            return True
        return False

    def _make_joints(self) -> List[Joint]:
        """Create the joints."""
        # Find the bundles at each point.
        horizontal: Dict[IntPoint, Bundle] = {}
        vertical: Dict[IntPoint, Bundle] = {}
        self._collect_bundles(horizontal, vertical)
        # Create the joints at each segment end.
        joints: List[Joint] = []
        jmap: Dict[IntPoint, Joint] = {}
        my_name = self._name
        for route in self._routes:
            for seg in route:
                for point in seg.grid_vector.points:
                    if point not in jmap:
                        hor = horizontal.get(point)
                        ver = vertical.get(point)
                        index = len(joints)
                        name = f"{my_name}.{index}"
                        joint = Joint(name, point, hor, ver)
                        joints.append(joint)
                        jmap[point] = joint
        return joints

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
            vec = bundle.grid_vector
            ori = vec.orientation
            col = collections[ori]
            for point in vec.through_points():
                col[point] = bundle

    def _map_points_to_joints(self) -> Dict[IntPoint, Joint]:
        """Return a map from a grid point to a joint."""
        jmap = {}
        for joint in self._joints:
            jmap[joint.point] = joint
        return jmap

    def _make_wires(self) -> List[Wire]:
        """Create the wires."""
        wires: List[Wire] = []
        jmap = self._joint_map
        for route in self._routes:
            wire_segments: List[WireSegment] = []
            route_segments = list(route)
            last_index = len(route_segments) - 1
            for i, rseg in enumerate(route_segments):
                vec = rseg.grid_vector
                joint_1 = jmap[vec.first_point]
                joint_2 = jmap[vec.last_point]
                is_first = i == 0
                is_last = i == last_index
                cseg = WireSegment(
                    route_segment=rseg,
                    start=joint_1, end=joint_2,
                    is_first=is_first, is_last=is_last,
                )
                wire_segments.append(cseg)
            wire = Wire(route, wire_segments)
            wires.append(wire)
        return wires

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
            vec = bundle.grid_vector
            ori = vec.orientation
            out = (point == vec.first_point)
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

    # In order to find bundles that overlap, the integer offsets are
    # converted to real numbers by multiplying with this quantity.
    _FACTOR = 0.001

    def _pretty_print(self, level: int = 0) -> None:
        """Print the object for debugging purposes."""
        print(indent(level) + repr(self) + ":")
        print(indent(level + 1) + "Bundles:")
        for bundle in self.bundles():
            bundle._pretty_print(level + 2)

######################################################################

class NetworkBundle:
    """Combination of a network and one of its bundles."""

    def __init__(self, network: Network, bundle: Bundle):
        """Initialize for the given bundle."""
        self._network = network
        self._bundle = bundle

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._bundle.description()
        return class_str(self, content)

    @property
    def network(self) -> Network:
        """The network to which the bundle belongs."""
        return self._network

    @property
    def bundle(self) -> Bundle:
        """The bundle."""
        return self._bundle

    def overlaps_with(self, other: 'NetworkBundle', use_offsets: bool) -> bool:
        """True if this bundle overlaps with the given one."""
        net1, bundle1 = self.network, self.bundle
        net2, bundle2 = other.network, other.bundle
        vec1 = bundle1.grid_vector
        vec2 = bundle2.grid_vector
        if vec1.axis != vec2.axis:
            return False
        p11, p12 = net1.offset_bundle(bundle1, use_offsets)
        p21, p22 = net2.offset_bundle(bundle2, use_offsets)
        horizontal = vec1.orientation.is_horizontal()
        vertical = not horizontal
        if horizontal and p11.x <= p22.x and p12.x >= p21.x:
            return True
        if vertical and p11.y <= p22.y and p12.y >= p21.y:
            return True
        return False

######################################################################

class BundleLayer:
    """Collection of bundles having the same offset."""

    def __init__(self, struct_name: str, offset: int):
        """Initialize an empty layer."""
        self._name = f"{struct_name}.{offset}"
        self._offset = offset
        self._net_bundles: List[NetworkBundle] = []

    def __repr__(self) -> str:
        """Represent as string."""
        return class_str(self, repr(self._name))

    def __iter__(self) -> Iterator[NetworkBundle]:
        """Iterate over the network bundles (in no particular order)."""
        yield from self._net_bundles

    @property
    def offset(self) -> int:
        """Common offset of the bundles in the layer."""
        return self._offset

    def append(self, net_bundle: NetworkBundle) -> None:
        """Add a network bundle to the layer."""
        self._net_bundles.append(net_bundle)

######################################################################

class BundleStructure:
    """Collection of overlapping bundles."""

    def __init__(
            self,
            axis: Axis,
            index: int,
            net_bundles: Iterable[NetworkBundle],
    ):
        """Initialize for the given bundles.

        The bundles will be arranged into layers according to their
        offsets.

        """
        self._axis = axis
        self._index = index
        self._name = f"{axis.name}.{index}"
        self._layers_by_offset = self._make_layers(net_bundles)

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._name)
        return class_str(self, content)

    def __iter__(self) -> Iterator[BundleLayer]:
        """Iterate over the layers in offset order."""
        by_offset = self._layers_by_offset
        for offset in sorted(by_offset):
            yield by_offset[offset]

    @property
    def name(self) -> str:
        """Name of the structure."""
        return self._name

    @property
    def axis(self) -> Axis:
        """Axis on which the bundles sit."""
        return self._axis

    def restructure(self) -> None:
        """Rearrange bundles into new layers.

        Note that this method discards the previous layers and also
        updates the offsets of the bundles!

        The process provides two benefits:

        a) On the one hand, it packs the bundles as densely as
           possible.

        b) On the other hand, it separates bundles that may overlap
           due to the insufficient overlap checks employed by the
           initial refining process.  Specifically, it solves problems
           like the one depicted below:

           |        |
           ,--      | ,--
           |    =>  | |
           `--      `-|--
           |          |

        """
        # Calculate the new offsets starting from the existing ones.
        # We can use a fresh graph.
        graph = nx.DiGraph()
        net_bundles = list(self._network_bundles())
        for i, net_bundle_1 in enumerate(net_bundles):
            bundle_1 = net_bundle_1.bundle
            for net_bundle_2 in net_bundles[:i]:
                bundle_2 = net_bundle_2.bundle
                # Caution: To restructure the layers, we *do* use the
                # offsets to calculate the overlap!
                if net_bundle_1.overlaps_with(net_bundle_2, True):
                    graph.add_node(bundle_1)
                    graph.add_node(bundle_2)
                    graph.add_edge(bundle_2, bundle_1)
        set_bundle_offsets(graph)
        # Create new layers using the new offsets.
        self._layers_by_offset = self._make_layers(net_bundles)

    def _make_layers(
            self,
            net_bundles: Iterable[NetworkBundle]
    ) -> Dict[int, BundleLayer]:
        """Group the given bundles into layers by offset."""
        result: Dict[int, BundleLayer] = {}
        for net_bundle in net_bundles:
            offset = net_bundle.bundle.offset
            if offset not in result:
                result[offset] = self._make_layer(offset)
            result[offset].append(net_bundle)
        return result

    def _network_bundles(self) -> Iterator[NetworkBundle]:
        """Iterate over the elements in offset order."""
        for layer in self:
            yield from layer

    def _make_layer(self, offset: int) -> BundleLayer:
        """Create a new empty layer."""
        return BundleLayer(self._name, offset)

######################################################################

def set_bundle_offsets(graph: nx.DiGraph) -> None:
    """Calculate the offsets and store them in the bundles."""
    for bundle in graph.nodes:
        bundle.offset = 0
    while True:
        updated = False
        for bundle_2 in graph.nodes:
            offset = 0
            for bundle_1 in graph.predecessors(bundle_2):
                offset = max(offset, bundle_1.offset + 1)
            if offset > bundle_2.offset:
                bundle_2.offset = offset
                updated = True
        if not updated:
            break
