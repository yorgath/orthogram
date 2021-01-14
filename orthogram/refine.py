"""Refine the results of the router."""

from enum import Enum, auto
from itertools import permutations

from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Sequence,
    Tuple,
)

import networkx as nx # type: ignore

from .debug import Debug

from .diagram import (
    Block,
    Connection,
    Node,
)

from .geometry import (
    Axis,
    Direction,
    FloatPoint,
    IntPoint,
    Orientation,
    OrientedVector,
)

from .route import (
    NodesAndPointsIterator,
    Route,
    RouteSegment,
    Router,
)

from .util import log_debug

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
        assert len(seg_list) > 0
        self._route_segments = seg_list
        seg = seg_list[0]
        self._axis = axis = seg.axis
        # Calculate the coordinate range.
        horizontal = axis.orientation is Orientation.HORIZONTAL
        coords = set()
        for seg in seg_list:
            for p in seg.through_points():
                if horizontal:
                    coords.add(p.j)
                else:
                    coords.add(p.i)
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
        else:
            return 0

    @property
    def vertical_offset(self) -> int:
        """Vertical offset."""
        bundle = self._horizontal_bundle
        if bundle:
            return bundle.offset
        else:
            return 0

    @property
    def node(self) -> Optional[Node]:
        """Node on which the joint lies."""
        return self._node

    @node.setter
    def node(self, node: Node) -> None:
        self._node = node

######################################################################

class WireSegment(OrientedVector):
    """Segment between two angles of a wire."""

    def __init__(self, route_segment: RouteSegment, start: Joint, end: Joint):
        """Initialize the wire."""
        self._route_segment = route_segment
        self._start = start
        self._end = end

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
        else:
            return joint.horizontal_offset

    @property
    def joints(self) -> Tuple[Joint, Joint]:
        """The joints at the two ends of the segment."""
        return self._start, self._end

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

    def joints(self) -> Iterator[Joint]:
        """Return an iterator over the joints of the wire."""
        done: Set[Joint] = set()
        for seg in self._segments:
            for joint in seg.joints:
                if joint not in done:
                    yield joint
                    done.add(joint)

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
        self._joints: Dict[IntPoint, Joint] = {}
        self._init_joints()
        self._wires: List[Wire] = []
        self._init_wires()

    def _init_bundles(self) -> None:
        """Create the bundles of segments."""
        # Use a graph to discover the interactions.
        graph = nx.Graph()
        segments = []
        for route in self._routes:
            for seg in route.segments():
                segments.append(seg)
                graph.add_node(seg)
        n = len(segments)
        for i in range(n):
            seg1 = segments[i]
            for j in range(i + 1, n):
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
        else:
            return False

    def _init_joints(self) -> None:
        """Create the joints."""
        # Find the bundles at each point.
        horizontal: Dict[IntPoint, Bundle] = {}
        vertical: Dict[IntPoint, Bundle] = {}
        collections = {
            Orientation.HORIZONTAL: horizontal,
            Orientation.VERTICAL: vertical,
        }
        for bundle in self._bundles:
            ori = bundle.orientation
            col = collections[ori]
            for p in bundle.through_points():
                col[p] = bundle
        # Create the joints at each segment end.
        joints = self._joints
        joints.clear()
        for route in self._routes:
            for seg in route.segments():
                points = [seg.first_point, seg.last_point]
                for p in points:
                    if p not in joints:
                        hor = horizontal.get(p)
                        ver = vertical.get(p)
                        joint = Joint(p, hor, ver)
                        joints[p] = joint

    def _init_wires(self) -> None:
        """Create the wires."""
        wires = self._wires
        wires.clear()
        joints = self._joints
        for route in self._routes:
            segments = []
            for rseg in route.segments():
                j1 = joints[rseg.first_point]
                j2 = joints[rseg.last_point]
                cseg = WireSegment(rseg, j1, j2)
                segments.append(cseg)
            wire = Wire(route, segments)
            wires.append(wire)

    def bundles(self) -> Iterator[Bundle]:
        """Return an iterator over the bundles of the network."""
        yield from self._bundles

    def wires(self) -> Iterator[Wire]:
        """Return an iterator over the calculated wires."""
        yield from self._wires

    def joints(self) -> Iterator[Joint]:
        """Return an iterator over all the joints of the network."""
        yield from self._joints.values()

    def offset_bundle(self, bundle: Bundle) -> Tuple[FloatPoint, FloatPoint]:
        """Return a pair of points suitable for overlap check."""
        j1 = self._joints[bundle.first_point]
        p1 = self._float_point(bundle, j1)
        j2 = self._joints[bundle.last_point]
        p2 = self._float_point(bundle, j2)
        return p1, p2

    # In order to find bundles that overlap, the integer offsets are
    # converted to real numbers by multiplying with this quantity.
    _FACTOR = 0.001

    def _float_point(self, bundle: Bundle, joint: Joint) -> FloatPoint:
        """Calculated using the central integer point and the offsets.

        If there is a node associated with the joint, the point is
        moved a bit to avoid bundles interacting at the nodes.

        """
        p = joint.point
        h = joint.horizontal_offset
        v = joint.vertical_offset
        if joint.node:
            ori = bundle.orientation
            out = (p == bundle.first_point)
            key = (ori, out)
            values = {
                (Orientation.VERTICAL, False): (0, -1),
                (Orientation.VERTICAL, True): (0, 1),
                (Orientation.HORIZONTAL, False): (-1, 0),
                (Orientation.HORIZONTAL, True): (1, 0),
            }
            dh, dv = values[key]
        else:
            dh = dv = 0
        f = self._FACTOR
        x = p.j + f * (h + dh)
        y = p.i + f * (v + dv)
        return FloatPoint(x, y)

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({},{};routes={};bundles={})".format(
            self.__class__.__name__,
            self._origin.name,
            self._group,
            len(self._routes),
            len(self._bundles),
        )

######################################################################

class Passthrough:
    """Passing of a route through a point."""

    def __init__(
            self,
            point: IntPoint,
            segment_in: Optional[RouteSegment],
            segment_out: Optional[RouteSegment],
    ):
        """Initialize for the given segments interacting at the point."""
        self._point = point
        bottom: Optional[RouteSegment] = None
        left: Optional[RouteSegment] = None
        right: Optional[RouteSegment] = None
        top: Optional[RouteSegment] = None
        Dir = Direction
        if segment_in:
            direc = segment_in.direction
            if direc is Dir.DOWN:
                top = segment_in
            elif direc is Dir.LEFT:
                right = segment_in
            elif direc is Dir.RIGHT:
                left = segment_in
            elif direc is Dir.UP:
                bottom = segment_in
        if segment_out:
            direc = segment_out.direction
            if direc is Dir.DOWN:
                bottom = segment_out
            elif direc is Dir.LEFT:
                left = segment_out
            elif direc is Dir.RIGHT:
                right = segment_out
            elif direc is Dir.UP:
                top = segment_out
        self._segment_bottom = bottom
        self._segment_left = left
        self._segment_right = right
        self._segment_top = top

    @property
    def point(self) -> IntPoint:
        """Point through which the route passes."""
        return self._point

    @property
    def segment_bottom(self) -> Optional[RouteSegment]:
        """Route segment at the bottom side."""
        return self._segment_bottom

    @property
    def segment_left(self) -> Optional[RouteSegment]:
        """Route segment at the left side."""
        return self._segment_left

    @property
    def segment_right(self) -> Optional[RouteSegment]:
        """Route segment at the right side."""
        return self._segment_right

    @property
    def segment_top(self) -> Optional[RouteSegment]:
        """Route segment at the top side."""
        return self._segment_top

    def segments(self) -> Iterator[RouteSegment]:
        """Return the segments passing through the point."""
        segments = [
            self._segment_bottom,
            self._segment_left,
            self._segment_right,
            self._segment_top,
        ]
        for seg in segments:
            if seg:
                yield seg

######################################################################

class Interaction:
    """Interaction of two routes at a point."""

    def __init__(self, p: IntPoint, pt1: Passthrough, pt2: Passthrough):
        """Initialize an interaction of two routes at a point."""
        self._point = p
        self._passthroughs = (pt1, pt2)

    @property
    def passthroughs(self) -> Tuple[Passthrough, Passthrough]:
        """Passthroughs of the routes that interact."""
        return self._passthroughs

######################################################################

class _RuleCategory(Enum):
    """Types of rules."""
    T = auto()
    V = auto()
    S = auto()

######################################################################

class _SegmentRule:
    """Declares that one route segment comes after another."""

    def __init__(
            self,
            category: _RuleCategory,
            first: RouteSegment,
            second: RouteSegment,
    ):
        """Initialize with the two segments."""
        assert first.orientation is second.orientation
        self._category = category
        self._first = first
        self._second = second

    @property
    def category(self) -> _RuleCategory:
        """Category of the rule."""
        return self._category

    @property
    def first(self) -> RouteSegment:
        """The segment that comes before."""
        return self._first

    @property
    def second(self) -> RouteSegment:
        """The segment that comes after."""
        return self._second

######################################################################

class _SegmentRuleFactory:

    def __init__(self, category: _RuleCategory):
        """Initialize for a given category of rules."""
        self._category = category

    def __call__(
            self,
            first: RouteSegment,
            second: RouteSegment,
    ) -> _SegmentRule:
        """Create a rule."""
        return _SegmentRule(self._category, first, second)

######################################################################

class _BundleRule:
    """Declares that one bundle comes after another."""

    def __init__(
            self,
            category: _RuleCategory,
            first: Bundle,
            second: Bundle,
    ):
        """Initialize with the two bundles."""
        assert first.orientation is second.orientation
        self._category = category
        self._first = first
        self._second = second

    def __repr__(self) -> str:
        """Convert to string."""
        if self._first.orientation is Orientation.HORIZONTAL:
            adverb = "OVER"
        else:
            adverb = "BEFORE"
        return "{}({}; {} {} {})".format(
            self.__class__.__name__,
            self._category.name,
            self._first, adverb, self._second,
        )

    @property
    def category(self) -> _RuleCategory:
        """Category of the rule."""
        return self._category

    @property
    def first(self) -> Bundle:
        """The bundle that comes before."""
        return self._first

    @property
    def second(self) -> Bundle:
        """The bundle that comes after."""
        return self._second

    def bundles(self) -> Iterator[Bundle]:
        """Return an iterator over the bundles."""
        yield self._first
        yield self._second

######################################################################

# Combination of a network and one of its bundles.
_NetworkAndBundle = Tuple[Network, Bundle]

######################################################################

class Refiner:
    """Used to refine the coarse results of the router."""

    def __init__(self, router: Router):
        """Initialize the refiner for the given router."""
        self._router = router
        self._networks: List[Network] = []
        self._init_networks()
        self._segment_bundles: Dict[RouteSegment, Bundle] = {}
        self._init_segment_bundles()
        self._update_offsets()

    def _init_networks(self) -> None:
        """Create the networks."""
        #
        # Group routes by connection group.  If the connection does
        # not belong to any group, make a group for the route alone.
        #
        collapse_connections = self._must_collapse_connections()
        K = Tuple[NetworkOrigin, str]
        per_group: Dict[K, List[Route]] = {}
        for route in self._router.routes():
            group = route.connection.group
            # Use an extra key to avoid name collisions.
            if group and collapse_connections:
                origin = NetworkOrigin.GROUP
            else:
                origin = NetworkOrigin.ROUTE
                group = route.name
            key = (origin, group)
            group_routes = per_group.get(key)
            if group_routes:
                group_routes.append(route)
            else:
                group_routes = [route]
                per_group[key] = group_routes
        nets = self._networks
        nets.clear()
        for key, group_routes in per_group.items():
            net = Network(*key, group_routes)
            self._set_joint_nodes(net)
            nets.append(net)

    def _must_collapse_connections(self) -> bool:
        """Collapse connections in the same group?"""
        return self._router.diagram.attributes.collapse_connections

    def _set_joint_nodes(self, net: Network) -> None:
        """Associate joints with nodes."""
        router = self._router
        for joint in net.joints():
            joint_node = router.node_at(joint.point)
            if joint_node:
                joint.node = joint_node

    def _init_segment_bundles(self) -> None:
        """Map each route segment to the bundle to which it belongs."""
        seg_bundles = self._segment_bundles
        seg_bundles.clear()
        for net in self._networks:
            for bundle in net.bundles():
                for seg in bundle.route_segments():
                    seg_bundles[seg] = bundle

    def _update_offsets(self) -> None:
        """Calculate the offsets of the bundles."""
        dag = self._bundle_dag()
        self._update_bundle_offsets(dag)
        self._stack_bundles()

    def _bundle_dag(self) -> nx.DiGraph:
        """Create a DAG of bundles out of the route interactions."""
        g = nx.DiGraph()
        seg_bundles = self._segment_bundles
        # The bundles are the nodes of the graph.
        interactions = list(self._interactions())
        for inter in interactions:
            for pt in inter.passthroughs:
                for seg in pt.segments():
                    bundle = seg_bundles[seg]
                    if bundle not in g:
                        g.add_node(bundle)
        # Edges represent the order of two bundles.
        tv_rules: List[_BundleRule] = []
        s_rules: List[Sequence[_BundleRule]] = []
        for inter in interactions:
            pt1, pt2 = inter.passthroughs
            # Store T and V rules one by one, because we roll them
            # back individually.
            seg_rule = self._t_rule(pt1, pt2)
            if seg_rule:
                bundle_rule = self._segment_rule_to_bundle_rule(seg_rule)
                tv_rules.append(bundle_rule)
            for seg_rule in self._v_rules(pt1, pt2):
                bundle_rule = self._segment_rule_to_bundle_rule(seg_rule)
                tv_rules.append(bundle_rule)
            # Store S rules as lists of rules, because we must be able
            # to roll back the whole list.
            for seg_rules in self._s_rules(pt1, pt2):
                bundle_rules = self._segment_rules_to_bundle_rules(seg_rules)
                s_rules.append(bundle_rules)
        for bundle_rule in tv_rules:
            self._try_add_rules_to_dag(g, [bundle_rule])
        for bundle_rules in s_rules:
            self._try_add_rules_to_dag(g, bundle_rules)
        return g

    def _interactions(self) -> Iterator[Interaction]:
        """Iterate over the interactions of the routes at each point."""
        # Collect the passthroughs at each point.
        per_point: Dict[IntPoint, List[Passthrough]] = {}
        for route in self._router.routes():
            for pt in self._passthroughs(route):
                p = pt.point
                pts = per_point.get(p)
                if not pts:
                    pts = []
                    per_point[p] = pts
                pts.append(pt)
        # Sort the points according to the number of passthroughs.
        # Starting from the less busy points appears to give better
        # results overall.
        items = []
        for p, pts in per_point.items():
            item = (len(pts), p)
            items.append(item)
        key = lambda item: item[0]
        sorted_items = sorted(items, key=key)
        points = [item[1] for item in sorted_items]
        # Create the interactions.
        for p in points:
            pts = per_point[p]
            for pt1, pt2 in permutations(pts, 2):
                inter = Interaction(p, pt1, pt2)
                yield inter

    def _passthroughs(self, route: Route) -> Iterator[Passthrough]:
        """Iterate over the points through which the route passes."""
        seg1: Optional[RouteSegment] = None
        for seg2 in route.segments():
            points = list(seg2.through_points())
            n = len(points)
            for i in range(n - 1):
                p = points[i]
                yield Passthrough(
                    point=p,
                    segment_in=seg1,
                    segment_out=seg2,
                )
                # Set previous segment for each point.
                seg1 = seg2
        # Last point of route.
        if seg1:
            points = list(seg1.through_points())
            yield Passthrough(
                point=points[-1],
                segment_in=seg1,
                segment_out=None,
            )

    def _t_rule(
            self,
            pt1: Passthrough,
            pt2: Passthrough
    ) -> Optional[_SegmentRule]:
        """Rule between segments for the T-junction interaction.

        The two routes interact like this:

        --+--
          |
          |

        """
        b1 = pt1.segment_bottom
        l1 = pt1.segment_left
        r1 = pt1.segment_right
        t1 = pt1.segment_top
        b2 = pt2.segment_bottom
        l2 = pt2.segment_left
        r2 = pt2.segment_right
        t2 = pt2.segment_top
        f = _SegmentRuleFactory(_RuleCategory.T)
        if False: pass
        elif b1 and l1 and b2 and r2: return f(b1, b2)
        elif b1 and l1 and b2 and t2: return f(b1, b2)
        elif b1 and l1 and l2 and r2: return f(l2, l1)
        elif b1 and l1 and l2 and t2: return f(l2, l1)
        elif b1 and r1 and b2 and t2: return f(b2, b1)
        elif b1 and r1 and l2 and r2: return f(r2, r1)
        elif b1 and r1 and r2 and t2: return f(r2, r1)
        elif b1 and t1 and l2 and t2: return f(t2, t1)
        elif b1 and t1 and r2 and t2: return f(t1, t2)
        elif l1 and r1 and l2 and t2: return f(l2, l1)
        elif l1 and r1 and r2 and t2: return f(r2, r1)
        elif l1 and t1 and r2 and t2: return f(t1, t2)
        else: return None

    def _v_rules(
            self,
            pt1: Passthrough,
            pt2: Passthrough
    ) -> Sequence[_SegmentRule]:
        """Rules for the vertex-to-vertex interaction.

        The two routes interact at a single point, like this:

          |
        --'
           '--
           |

        The method returns two rules for each case; *either* one of
        them will do.

        """
        b1 = pt1.segment_bottom
        l1 = pt1.segment_left
        r1 = pt1.segment_right
        t1 = pt1.segment_top
        b2 = pt2.segment_bottom
        l2 = pt2.segment_left
        r2 = pt2.segment_right
        t2 = pt2.segment_top
        f = _SegmentRuleFactory(_RuleCategory.V)
        if False: pass
        elif b1 and l1 and r2 and t2: return [f(b1, t2), f(r2, l1)]
        elif b1 and r1 and l2 and t2: return [f(l2, r1), f(t2, b1)]
        else: return []

    def _s_rules(
            self,
            pt1: Passthrough,
            pt2: Passthrough
    ) -> Iterable[Sequence[_SegmentRule]]:
        """Rules for the "spoon" interaction.

        The two routes interact like this:

        ||
        |`--
        `---

        This method returns *pairs* of rules; either both rules of a
        pair must be added to the DAG or neither.  However, either
        pair will do.

        """
        b1 = pt1.segment_bottom
        l1 = pt1.segment_left
        r1 = pt1.segment_right
        t1 = pt1.segment_top
        b2 = pt2.segment_bottom
        l2 = pt2.segment_left
        r2 = pt2.segment_right
        t2 = pt2.segment_top
        f = _SegmentRuleFactory(_RuleCategory.S)
        if False:
            pass
        elif b1 and l1 and b2 and l2:
            return [
                [f(b1, b2), f(l2, l1)],
                [f(b2, b1), f(l1, l2)],
            ]
        elif b1 and r1 and b2 and r2:
            return [
                [f(b1, b2), f(r1, r2)],
                [f(b2, b1), f(r2, r1)],
            ]
        elif l1 and t1 and l2 and t2:
            return [
                [f(l1, l2), f(t1, t2)],
                [f(l2, l1), f(t2, t1)],
            ]
        elif r1 and t1 and r2 and t2:
            return [
                [f(r2, r1), f(t1, t2)],
                [f(r1, r2), f(t2, t1)],
            ]
        else:
            return []

    def _bundle_rules(
            self,
            rules: Sequence[_SegmentRule]
    ) -> Sequence[_BundleRule]:
        """Convert segment rules to a bundle rules."""
        bundle_rules = []
        for rule in rules:
            bundle_rule = self._segment_rule_to_bundle_rule(rule)
            bundle_rules.append(bundle_rule)
        return bundle_rules

    def _segment_rules_to_bundle_rules(
            self,
            rules: Sequence[_SegmentRule],
    ) -> Sequence[_BundleRule]:
        """Convert a sequence of segment rules to a bundle rules."""
        bundle_rules = []
        for rule in rules:
            bundle_rule = self._segment_rule_to_bundle_rule(rule)
            bundle_rules.append(bundle_rule)
        return bundle_rules

    def _segment_rule_to_bundle_rule(self, rule: _SegmentRule) -> _BundleRule:
        """Convert a segment rule to a bundle rule."""
        seg_bundles = self._segment_bundles
        bundle1 = seg_bundles[rule.first]
        bundle2 = seg_bundles[rule.second]
        return _BundleRule(rule.category, bundle1, bundle2)

    def _try_add_rules_to_dag(
            self,
            g: nx.DiGraph,
            rules: Sequence[_BundleRule],
    ) -> None:
        """Try to add the rules as edges to the DAG.

        It rolls back all the edges if one of them causes a cycle.

        """
        added = []
        ok = True
        for rule in rules:
            bundle1 = rule.first
            bundle2 = rule.second
            # Do not use the bundle against itself!
            if bundle1 is bundle2:
                continue
            # Do not add the same rule twice.
            if g.has_edge(bundle1, bundle2):
                continue
            g.add_edge(bundle1, bundle2)
            added.append((bundle1, bundle2))
            # Abort if there are cycles.
            if not nx.is_directed_acyclic_graph(g):
                ok = False
                break
        if ok:
            if Debug.is_enabled():
                for rule in rules:
                    log_debug("Added {}".format(rule))
        if not ok:
            # Remove the edges in case of cycles.
            for e in added:
                g.remove_edge(*e)
            if Debug.is_enabled():
                for rule in rules:
                    log_debug("Rejected {}".format(rule))

    def _update_bundle_offsets(self, g: nx.DiGraph) -> None:
        """Calculate the offsets and store them in the bundles."""
        # Assign inital depths to the nodes.
        nodes = g.nodes
        for bundle in nodes:
            is_root = True
            for _ in g.predecessors(bundle):
                is_root = False
                break
            if is_root:
                nodes[bundle]['depth'] = 0
            else:
                nodes[bundle]['depth'] = -1
        # Calculate the depths of all the nodes.
        while True:
            changed = False
            for bundle1 in nodes:
                depth1 = nodes[bundle1]['depth']
                if depth1 >= 0:
                    for bundle2 in g.successors(bundle1):
                        depth2 = nodes[bundle2]['depth']
                        if depth1 + 1 > depth2:
                            nodes[bundle2]['depth'] = max(depth1 + 1, depth2)
                            changed = True
            if not changed:
                break
        # We can now store the offsets in the bundles.
        for bundle in nodes:
            offset = nodes[bundle]['depth']
            bundle.offset = offset

    def _stack_bundles(self) -> None:
        """Second pass of the refinement process.

        The bundles calculated by the first pass are "stacked" as
        densely as possible on both sides of the axis.  The new
        offsets are stored back in the bundles.

        """
        # Group the bundles by axis.
        parallel: Dict[Axis, List[_NetworkAndBundle]] = {}
        for net in self._networks:
            for bundle in net.bundles():
                axis = bundle.axis
                if not axis in parallel:
                    parallel[axis] = []
                parallel[axis].append((net, bundle))
        # Stack the bundles of an axis as densely as possible.
        for axis_nbs in parallel.values():
            for over_nbs in self._overlapping_bundles(axis_nbs):
                rows = self._stack_overlapping_bundles(over_nbs)
                # Center offsets around zero.
                mid = len(rows) // 2
                for i, nbs in enumerate(rows):
                    for nb in nbs:
                        bundle = nb[1]
                        bundle.offset = i - mid

    def _overlapping_bundles(
            self,
            nbs: Iterable[_NetworkAndBundle]
    ) -> Iterator[Iterable[_NetworkAndBundle]]:
        """Separate the bundles into collections of overlapping bundles.

        This method checks for overlapping bundles at the grid level.
        It does not use the offsets calculated in the previous steps
        at all.

        """
        #
        # Use an undirected graph to find the sets of overlapping
        # bundles.  The bundles will be the nodes of the graph.  If
        # two bundles overlap, add an edge between them.  The
        # connected components of the resulting graph are the sets
        # that we are after.
        #
        nbs = list(nbs)
        g = nx.Graph()
        for nb in nbs:
            bundle = nb[1]
            g.add_node(bundle, nb=nb)
        for i, nb1 in enumerate(nbs):
            _, bundle1 = nb1
            for nb2 in nbs[i + 1:]:
                _, bundle2 = nb2
                if self._bundles_overlap(nb1, nb2):
                    g.add_edge(bundle1, bundle2)
        for bundles in nx.connected_components(g):
            block = []
            for bundle in bundles:
                nb = g.nodes[bundle]['nb']
                block.append(nb)
            yield block

    def _stack_overlapping_bundles(
            self,
            nbs: Iterable[_NetworkAndBundle]
    ) -> Sequence[Sequence[_NetworkAndBundle]]:
        """Stack collinear bundles so that they do not overlap."""
        key = lambda nb: nb[1].offset
        nbs = sorted(nbs, key=key)
        result: List[List[_NetworkAndBundle]] = []
        for nb in nbs:
            overlap_on = -1
            n = len(result)
            for i in range(n - 1, -1, -1):
                row = result[i]
                for nb2 in row:
                    if self._bundles_overlap(nb, nb2):
                        overlap_on = i
                        break
                if overlap_on >= 0:
                    break
            if overlap_on == n - 1:
                # New row.
                result.append([nb])
            else:
                # Append to existing row.
                result[overlap_on + 1].append(nb)
        return result

    @staticmethod
    def _bundles_overlap(
            nb1: _NetworkAndBundle,
            nb2: _NetworkAndBundle
    ) -> bool:
        """True if the two bundles overlap.

        This method takes into account the offsets calculated in the
        previous steps.

        """
        net1, bundle1 = nb1
        net2, bundle2 = nb2
        if bundle1.axis != bundle2.axis:
            return False
        p11, p12 = net1.offset_bundle(bundle1)
        p21, p22 = net2.offset_bundle(bundle2)
        horizontal = bundle1.orientation is Orientation.HORIZONTAL
        vertical = not horizontal
        if horizontal and p11.x <= p22.x and p12.x >= p21.x:
            return True
        elif vertical and p11.y <= p22.y and p12.y >= p21.y:
            return True
        else:
            return False

    def networks(self) -> Iterator[Network]:
        """Return an iterator over the calculated networks."""
        yield from self._networks
