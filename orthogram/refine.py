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

import igraph # type: ignore

from .debug import Debug
from .diagram import Link, Pin

from .geometry import (
    Direction,
    FloatPoint,
    IntPoint,
    Orientation,
    OrientedVector,
)

from .route import (
    LayoutAxis,
    PinsAndPointsIterator,
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

    def __init__(self, name: str, route_segments: Iterable[RouteSegment]):
        """Initialize with the given route segments.

        At least one route segment must be given.  This is necessary
        in order to compute the properties of the bundle.  Empty
        bundles cannot exist.

        The name must be unique among all the bundles in the layout,
        because it is used as a key in graphs.

        """
        self._name = name
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
        return "{}({};{};{}->{})".format(
            self.__class__.__name__,
            self._name,
            self._axis,
            coords[0],
            coords[1],
        )

    @property
    def name(self) -> str:
        """Name that identifies the bundle."""
        return self._name

    @property
    def axis(self) -> LayoutAxis:
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
            pin: Optional[Pin] = None,
    ):
        """Initialize the joint at the meeting point of the two bundles."""
        self._point = point
        self._horizontal_bundle = horizontal
        self._vertical_bundle = vertical
        self._pin = pin

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
    def pin(self) -> Optional[Pin]:
        """Terminal pin on which the joint lies."""
        return self._pin

    @pin.setter
    def pin(self, pin: Pin) -> None:
        self._pin = pin

######################################################################

class ConnectorSegment(OrientedVector):
    """Segment of a connector between two angles."""

    def __init__(self, route_segment: RouteSegment, start: Joint, end: Joint):
        """Initialize the connector."""
        self._route_segment = route_segment
        self._start = start
        self._end = end

    @property
    def axis(self) -> LayoutAxis:
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

class Connector:
    """Connector between two terminals."""

    def __init__(self, route: Route, segments: Sequence[ConnectorSegment]):
        """Create a connector with the given segments for a route."""
        self._route = route
        self._segments = list(segments)

    def segments(self) -> Iterator[ConnectorSegment]:
        """Return an iterator over the segments."""
        yield from self._segments

    @property
    def link(self) -> Link:
        """Associated link."""
        return self._route.link

    def joints(self) -> Iterator[Joint]:
        """Return an iterator over the joints of the connector."""
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
            name: str,
            origin: NetworkOrigin,
            group: str,
            routes: Iterable[Route]
    ):
        """Initialize with the given routes."""
        #
        self._name = name
        self._origin = origin
        self._group = group
        self._routes = list(routes)
        self._bundles: List[Bundle] = []
        self._joints: Dict[IntPoint, Joint] = {}
        self._connectors: List[Connector] = []
        #
        self._init_bundles()
        self._init_joints()
        self._init_connectors()

    def _init_bundles(self) -> None:
        """Create the bundles of segments."""
        # Use a graph to discover the interactions.
        graph = igraph.Graph(directed=False)
        segments = []
        for route in self._routes:
            for seg in route.segments():
                segments.append(seg)
                graph.add_vertex(seg.name, segment=seg)
        n = len(segments)
        for i in range(n):
            seg1 = segments[i]
            for j in range(i + 1, n):
                seg2 = segments[j]
                if self._segments_interact(seg1, seg2):
                    graph.add_edge(seg1.name, seg2.name)
        bundles = self._bundles
        bundles.clear()
        done = set()
        for idxs in graph.components():
            bundle_segments = []
            for idx in idxs:
                v = graph.vs[idx]
                seg = v['segment']
                bundle_segments.append(seg)
                done.add(seg)
            name = "{}.{}".format(self._name, len(bundles))
            bundle = Bundle(name, bundle_segments)
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

    def _init_connectors(self) -> None:
        """Create the connectors."""
        connectors = self._connectors
        connectors.clear()
        joints = self._joints
        for route in self._routes:
            segments = []
            for rseg in route.segments():
                j1 = joints[rseg.first_point]
                j2 = joints[rseg.last_point]
                cseg = ConnectorSegment(rseg, j1, j2)
                segments.append(cseg)
            conn = Connector(route, segments)
            connectors.append(conn)

    def bundles(self) -> Iterator[Bundle]:
        """Return an iterator over the bundles of the network."""
        yield from self._bundles

    def connectors(self) -> Iterator[Connector]:
        """Return an iterator over the calculated connectors."""
        yield from self._connectors

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

        If there is a pin associated with the joint, the point is
        moved a bit to avoid bundles interacting at the pins.

        """
        p = joint.point
        h = joint.horizontal_offset
        v = joint.vertical_offset
        if joint.pin:
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

    def drawing_priority(self) -> int:
        """Return a drawing priority for all the links.

        It returns the highest priority of all the links in the
        network.

        """
        net_pri = None
        for conn in self._connectors:
            link_pri = conn.link.attributes.drawing_priority
            if net_pri is None:
                net_pri = link_pri
            else:
                net_pri = max(net_pri, link_pri)
        if net_pri is None:
            net_pri = 0
        return net_pri

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

# Combination of a network and one of its bundles.
_NetworkAndBundle = Tuple[Network, Bundle]

######################################################################

class _Rule:
    """Declares that one route segment comes after another."""

    def __init__(self, first: RouteSegment, second: RouteSegment):
        """Initialize with the two segments."""
        assert first.orientation is second.orientation
        self._first = first
        self._second = second

    def __repr__(self) -> str:
        """Convert to string."""
        if self._first.orientation is Orientation.HORIZONTAL:
            adverb = "OVER"
        else:
            adverb = "BEFORE"
        return "{}({} {} {})".format(
            self.__class__.__name__,
            self._first, adverb, self._second,
        )

    @property
    def first(self) -> RouteSegment:
        """The segment that comes before."""
        return self._first

    @property
    def second(self) -> RouteSegment:
        """The segment that comes after."""
        return self._second

######################################################################

class Refiner:
    """Used to refine the coarse results of the router."""

    def __init__(self, router: Router):
        """Initialize the refiner for the given router."""
        self._router = router
        self._networks: List[Network] = []
        self._segment_bundles: Dict[RouteSegment, Bundle] = {}
        #
        self._init_networks()
        self._init_segment_bundles()
        self._update_offsets()

    def _init_networks(self) -> None:
        """Create the networks."""
        #
        # Group routes by link group.  If the link does not belong to
        # any group, make a group for the route alone.
        #
        collapse_links = self._must_collapse_links()
        K = Tuple[NetworkOrigin, str]
        per_group: Dict[K, List[Route]] = {}
        for route in self._router.routes():
            group = route.link.attributes.group
            # Use an extra key to avoid name collisions.
            if group and collapse_links:
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
            name = "N{}".format(len(nets))
            net = Network(name, *key, group_routes)
            self._set_joint_pins(net)
            nets.append(net)

    def _must_collapse_links(self) -> bool:
        """Collapse links in the same group?"""
        return self._router.diagram.attributes.collapse_links

    def _set_joint_pins(self, net: Network) -> None:
        """Associate joints with terminal pins."""
        router = self._router
        for joint in net.joints():
            joint_pin = router.pin_at(joint.point)
            if joint_pin:
                joint.pin = joint_pin

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

    def _bundle_dag(self) -> igraph.Graph:
        """Create a DAG of bundles out of the route interactions."""
        g = igraph.Graph(directed=True)
        seg_bundles = self._segment_bundles
        added = set()
        # The bundles are the vertices of the graph.
        interactions = list(self._interactions())
        for inter in interactions:
            for pt in inter.passthroughs:
                for seg in pt.segments():
                    bundle = seg_bundles[seg]
                    name = bundle.name
                    if name not in added:
                        attrs = {
                            'name': [name],
                            'bundle': [bundle],
                        }
                        g.add_vertices(1, attrs)
                        added.add(name)
        # Edges represent the order of two bundles.
        tv_rules = []
        s_rules = []
        for inter in interactions:
            pt1, pt2 = inter.passthroughs
            # Store T and V rules one by one, because we roll them
            # back individually.
            rule = self._t_rule(pt1, pt2)
            if rule:
                tv_rules.append(rule)
            for rule in self._v_rules(pt1, pt2):
                tv_rules.append(rule)
            # Store S rules as lists of rules, because we must be able
            # to roll back the whole list.
            for rules in self._s_rules(pt1, pt2):
                s_rules.append(rules)
        for rule in tv_rules:
            self._try_add_rules_to_dag(g, [rule])
        for rules in s_rules:
            self._try_add_rules_to_dag(g, rules)
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
        # Create the interactions.
        for p, pts in per_point.items():
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

    def _t_rule(self, pt1: Passthrough, pt2: Passthrough) -> Optional[_Rule]:
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
        R = _Rule
        if False: pass
        elif b1 and l1 and b2 and r2: return R(b1, b2)
        elif b1 and l1 and b2 and t2: return R(b1, b2)
        elif b1 and l1 and l2 and r2: return R(l2, l1)
        elif b1 and l1 and l2 and t2: return R(l2, l1)
        elif b1 and r1 and b2 and t2: return R(b2, b1)
        elif b1 and r1 and l2 and r2: return R(r2, r1)
        elif b1 and r1 and r2 and t2: return R(r2, r1)
        elif b1 and t1 and l2 and t2: return R(t2, t1)
        elif b1 and t1 and r2 and t2: return R(t1, t2)
        elif l1 and r1 and l2 and t2: return R(l2, l1)
        elif l1 and r1 and r2 and t2: return R(r2, r1)
        elif l1 and t1 and r2 and t2: return R(t1, t2)
        else: return None

    def _v_rules(self, pt1: Passthrough, pt2: Passthrough) -> Sequence[_Rule]:
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
        R = _Rule
        if False: pass
        elif b1 and l1 and r2 and t2: return [R(b1, t2), R(r2, l1)]
        elif b1 and r1 and l2 and t2: return [R(l2, r1), R(t2, b1)]
        else: return []

    def _s_rules(
            self,
            pt1: Passthrough,
            pt2: Passthrough
    ) -> Iterable[Sequence[_Rule]]:
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
        R = _Rule
        if False:
            pass
        elif b1 and l1 and b2 and l2:
            return [
                [R(b1, b2), R(l2, l1)],
                [R(b2, b1), R(l1, l2)],
            ]
        elif b1 and r1 and b2 and r2:
            return [
                [R(b1, b2), R(r1, r2)],
                [R(b2, b1), R(r2, r1)],
            ]
        elif l1 and t1 and l2 and t2:
            return [
                [R(l1, l2), R(t1, t2)],
                [R(l2, l1), R(t2, t1)],
            ]
        elif r1 and t1 and r2 and t2:
            return [
                [R(r2, r1), R(t1, t2)],
                [R(r1, r2), R(t2, t1)],
            ]
        else:
            return []

    def _try_add_rules_to_dag(
            self,
            g: igraph.Graph,
            rules: Sequence[_Rule]
    ) -> None:
        """Try to add the rules as edges to the DAG.

        It rolls back all the edges if one of them causes a cycle.

        """
        seg_bundles = self._segment_bundles
        added = []
        ok = True
        for rule in rules:
            bundle1 = seg_bundles[rule.first]
            bundle2 = seg_bundles[rule.second]
            # Do not use the bundle against itself!
            if bundle1 is bundle2:
                continue
            name1 = bundle1.name
            name2 = bundle2.name
            g.add_edge(name1, name2)
            added.append((name1, name2))
            # Abort if there are cycles.
            if not g.is_dag():
                ok = False
                break
        if ok:
            if Debug.debug:
                for rule in rules:
                    log_debug("Added {}".format(rule))
        if not ok:
            # Remove the edges in case of cycles.
            for e in added:
                g.delete_edges(e)
            if Debug.debug:
                for rule in rules:
                    log_debug("Rejected {}".format(rule))

    def _update_bundle_offsets(self, g: igraph.Graph) -> None:
        """Calculate the offsets and store them in the bundles."""
        # Assign inital depths to the vertices.
        for v in g.vs:
            is_root = True
            for idx in g.predecessors(v):
                is_root = False
                break
            if is_root:
                v['depth'] = 0
            else:
                v['depth'] = -1
        # Calculate the depths of all the vertices.
        while True:
            changed = False
            for v1 in g.vs:
                depth1 = v1['depth']
                if depth1 >= 0:
                    for idx2 in g.successors(v1):
                        v2 = g.vs[idx2]
                        depth2 = v2['depth']
                        if depth1 + 1 > depth2:
                            v2['depth'] = max(depth1 + 1, depth2)
                            changed = True
            if not changed:
                break
        # We can now store the offsets in the bundles.
        for v in g.vs:
            bundle = v['bundle']
            offset = v['depth']
            bundle.offset = offset

    def _stack_bundles(self) -> None:
        """Second pass of the refinement process.

        The bundles calculated by the first pass are "stacked" as
        densely as possible on both sides of the axis.  The new
        offsets are stored back in the bundles.

        """
        # Group the bundles by axis.
        parallel: Dict[LayoutAxis, List[_NetworkAndBundle]] = {}
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
        # bundles.  The bundles will be the vertices of the graph.  If
        # two bundles overlap, add an edge between them.  The
        # connected components of the resulting graph are the sets
        # that we are after.
        #
        nbs = list(nbs)
        g = igraph.Graph(directed=False)
        for nb in nbs:
            bundle = nb[1]
            name = bundle.name
            g.add_vertex(name, nb=nb)
        for i, nb1 in enumerate(nbs):
            (net1, bundle1) = nb1
            name1 = bundle1.name
            for nb2 in nbs[i + 1:]:
                net2, bundle2 = nb2
                if self._bundles_overlap(nb1, nb2):
                    name2 = bundle2.name
                    g.add_edge(name1, name2)
        for idxs in g.components():
            block = []
            for idx in idxs:
                v = g.vs[idx]
                block.append(v['nb'])
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
