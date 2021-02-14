"""Refine the results of the router."""

from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum, auto
from itertools import permutations

from typing import (
    Callable,
    Iterable,
    Iterator,
    List,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
)

import networkx as nx # type: ignore

from .net import (
    Bundle,
    Network,
    NetworkOrigin,
    WireSegment,
)

from ..debug import Debug

from ..geometry import (
    Axis,
    Direction,
    IntPoint,
    Orientation,
)

from ..util import log_debug

from .route import (
    Route,
    RouteSegment,
    Router,
)

######################################################################

class _Passthrough:
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

@dataclass
class _Interaction:
    """Interaction of two routes at a point."""
    point: IntPoint
    passthroughs: Tuple[_Passthrough, _Passthrough]

######################################################################

class _RuleCategory(Enum):
    """Types of rules."""
    T = auto()
    V = auto()
    S = auto()

######################################################################

@dataclass
class _SegmentRule:
    """Declares that one route segment comes after another."""
    category: _RuleCategory
    first: RouteSegment
    second: RouteSegment

    def __post_init__(self) -> None:
        """Do some runtime checks."""
        assert self.first.orientation is self.second.orientation

######################################################################

# This is the type of factory functions that create segment rules for
# a predefined rule category.
_SegmentRuleFactory = Callable[[RouteSegment, RouteSegment], _SegmentRule]

def _segment_rule_factory(category: _RuleCategory) -> _SegmentRuleFactory:
    """Return a function that creates segment rules of the given category."""
    def factory(
            first: RouteSegment, second: RouteSegment,
            category: _RuleCategory = category,
    ) -> _SegmentRule:
        return _SegmentRule(category, first, second)
    return factory

######################################################################

@dataclass(repr=False)
class _BundleRule:
    """Declares that one bundle comes after another."""
    category: _RuleCategory
    first: Bundle
    second: Bundle

    def __post_init__(self) -> None:
        """Do some runtime checks."""
        assert self.first.orientation is self.second.orientation

    def __repr__(self) -> str:
        """Convert to string."""
        if self.first.orientation is Orientation.HORIZONTAL:
            adverb = "OVER"
        else:
            adverb = "BEFORE"
        return "{}({}; {} {} {})".format(
            self.__class__.__name__,
            self.category.name,
            self.first, adverb, self.second,
        )

    def bundles(self) -> Iterator[Bundle]:
        """Return an iterator over the bundles."""
        yield self.first
        yield self.second

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
        self._segment_bundles: MutableMapping[
            RouteSegment, Bundle] = OrderedDict()
        self._init_segment_bundles()
        self._update_offsets()

    @property
    def router(self) -> Router:
        """The router whose results this object refines."""
        return self._router

    def networks(self) -> Iterator[Network]:
        """Return an iterator over the calculated networks."""
        yield from self._networks

    def segment_intersections(self, segment: WireSegment) -> Sequence[int]:
        """Returns the intersections of the segment by other segments."""
        intersections = set()
        for other in self._wire_segments():
            if other is not segment:
                cut = segment.cut_by(other)
                if cut:
                    intersections.add(cut)
        return sorted(intersections)

    def _wire_segments(self) -> Iterator[WireSegment]:
        """Returns the wire segments."""
        for net in self._networks:
            for wire in net.wires():
                yield from wire.segments()

    def _init_networks(self) -> None:
        """Create the networks."""
        #
        # Group routes by connection group.  If the connection does
        # not belong to any group, make a group for the route alone.
        #
        collapse_connections = self._must_collapse_connections()
        K = Tuple[NetworkOrigin, str]
        per_group: MutableMapping[K, List[Route]] = OrderedDict()
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
        graph = nx.DiGraph()
        interactions = list(self._interactions())
        # The bundles are the nodes of the graph.
        self._add_bundles_to_dag(graph, interactions)
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
            self._try_add_rules_to_dag(graph, [bundle_rule])
        for bundle_rules in s_rules:
            self._try_add_rules_to_dag(graph, bundle_rules)
        return graph

    def _add_bundles_to_dag(
            self,
            graph: nx.DiGraph,
            interactions: Iterable[_Interaction],
    ) -> None:
        """Add the bundles to the DAG as nodes."""
        seg_bundles = self._segment_bundles
        for inter in interactions:
            for passthrough in inter.passthroughs:
                for seg in passthrough.segments():
                    bundle = seg_bundles[seg]
                    if bundle not in graph:
                        graph.add_node(bundle)

    def _interactions(self) -> Iterator[_Interaction]:
        """Iterate over the interactions of the routes at each point."""
        # Collect the passthroughs at each point.
        per_point: MutableMapping[IntPoint, List[_Passthrough]] = OrderedDict()
        for route in self._router.routes():
            for passthrough in self._passthroughs(route):
                point = passthrough.point
                passthroughs = per_point.get(point)
                if not passthroughs:
                    passthroughs = []
                    per_point[point] = passthroughs
                passthroughs.append(passthrough)
        # Sort the points according to the number of passthroughs.
        # Starting from the less busy points appears to give better
        # results overall.
        items = []
        for point, passthroughs in per_point.items():
            item = (len(passthroughs), point)
            items.append(item)
        key = lambda item: item[0]
        sorted_items = sorted(items, key=key)
        points = [item[1] for item in sorted_items]
        # Create the interactions.
        for point in points:
            passthroughs = per_point[point]
            for passthrough_1, passthrough_2 in permutations(passthroughs, 2):
                inter = _Interaction(point, (passthrough_1, passthrough_2))
                yield inter

    @staticmethod
    def _passthroughs(route: Route) -> Iterator[_Passthrough]:
        """Iterate over the points through which the route passes."""
        seg1: Optional[RouteSegment] = None
        for seg2 in route.segments():
            points = list(seg2.through_points())
            n_points = len(points)
            for i in range(n_points - 1):
                point = points[i]
                yield _Passthrough(
                    point=point,
                    segment_in=seg1,
                    segment_out=seg2,
                )
                # Set previous segment for each point.
                seg1 = seg2
        # Last point of route.
        if seg1:
            points = list(seg1.through_points())
            yield _Passthrough(
                point=points[-1],
                segment_in=seg1,
                segment_out=None,
            )

    @staticmethod
    def _t_rule(
            passthrough_1: _Passthrough,
            passthrough_2: _Passthrough
    ) -> Optional[_SegmentRule]:
        """Rule between segments for the T-junction interaction.

        The two routes interact like this:

        --+--
          |
          |

        """
        bot_1 = passthrough_1.segment_bottom
        lef_1 = passthrough_1.segment_left
        rig_1 = passthrough_1.segment_right
        top_1 = passthrough_1.segment_top
        bot_2 = passthrough_2.segment_bottom
        lef_2 = passthrough_2.segment_left
        rig_2 = passthrough_2.segment_right
        top_2 = passthrough_2.segment_top
        make = _segment_rule_factory(_RuleCategory.T)
        result = None
        if bot_1 and lef_1 and bot_2 and rig_2:
            result = make(bot_1, bot_2)
        elif bot_1 and lef_1 and bot_2 and top_2:
            result = make(bot_1, bot_2)
        elif bot_1 and lef_1 and lef_2 and rig_2:
            result = make(lef_2, lef_1)
        elif bot_1 and lef_1 and lef_2 and top_2:
            result = make(lef_2, lef_1)
        elif bot_1 and rig_1 and bot_2 and top_2:
            result = make(bot_2, bot_1)
        elif bot_1 and rig_1 and lef_2 and rig_2:
            result = make(rig_2, rig_1)
        elif bot_1 and rig_1 and rig_2 and top_2:
            result = make(rig_2, rig_1)
        elif bot_1 and top_1 and lef_2 and top_2:
            result = make(top_2, top_1)
        elif bot_1 and top_1 and rig_2 and top_2:
            result = make(top_1, top_2)
        elif lef_1 and rig_1 and lef_2 and top_2:
            result = make(lef_2, lef_1)
        elif lef_1 and rig_1 and rig_2 and top_2:
            result = make(rig_2, rig_1)
        elif lef_1 and top_1 and rig_2 and top_2:
            result = make(top_1, top_2)
        return result

    @staticmethod
    def _v_rules(
            passthrough_1: _Passthrough,
            passthrough_2: _Passthrough
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
        bot_1 = passthrough_1.segment_bottom
        lef_1 = passthrough_1.segment_left
        rig_1 = passthrough_1.segment_right
        lef_2 = passthrough_2.segment_left
        rig_2 = passthrough_2.segment_right
        top_2 = passthrough_2.segment_top
        make = _segment_rule_factory(_RuleCategory.V)
        if bot_1 and lef_1 and rig_2 and top_2:
            return [make(bot_1, top_2), make(rig_2, lef_1)]
        if bot_1 and rig_1 and lef_2 and top_2:
            return [make(lef_2, rig_1), make(top_2, bot_1)]
        return []

    @staticmethod
    def _s_rules(
            passthrough_1: _Passthrough,
            passthrough_2: _Passthrough
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
        bot_1 = passthrough_1.segment_bottom
        lef_1 = passthrough_1.segment_left
        rig_1 = passthrough_1.segment_right
        top_1 = passthrough_1.segment_top
        bot_2 = passthrough_2.segment_bottom
        lef_2 = passthrough_2.segment_left
        rig_2 = passthrough_2.segment_right
        top_2 = passthrough_2.segment_top
        make = _segment_rule_factory(_RuleCategory.S)
        if bot_1 and lef_1 and bot_2 and lef_2:
            return [
                [make(bot_1, bot_2), make(lef_2, lef_1)],
                [make(bot_2, bot_1), make(lef_1, lef_2)],
            ]
        if bot_1 and rig_1 and bot_2 and rig_2:
            return [
                [make(bot_1, bot_2), make(rig_1, rig_2)],
                [make(bot_2, bot_1), make(rig_2, rig_1)],
            ]
        if lef_1 and top_1 and lef_2 and top_2:
            return [
                [make(lef_1, lef_2), make(top_1, top_2)],
                [make(lef_2, lef_1), make(top_2, top_1)],
            ]
        if rig_1 and top_1 and rig_2 and top_2:
            return [
                [make(rig_2, rig_1), make(top_1, top_2)],
                [make(rig_1, rig_2), make(top_2, top_1)],
            ]
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

    @staticmethod
    def _try_add_rules_to_dag(
            graph: nx.DiGraph,
            rules: Sequence[_BundleRule],
    ) -> None:
        """Try to add the rules as edges to the DAG.

        It rolls back all the edges if one of them causes a cycle.

        """
        added = []
        success = True
        for rule in rules:
            bundle1 = rule.first
            bundle2 = rule.second
            # Do not use the bundle against itself!
            if bundle1 is bundle2:
                continue
            # Do not add the same rule twice.
            if graph.has_edge(bundle1, bundle2):
                continue
            graph.add_edge(bundle1, bundle2)
            added.append((bundle1, bundle2))
            # Abort if there are cycles.
            if not nx.is_directed_acyclic_graph(graph):
                success = False
                break
        if success:
            if Debug.is_enabled():
                for rule in rules:
                    log_debug("Added {}".format(rule))
        if not success:
            # Remove the edges in case of cycles.
            for edge in added:
                graph.remove_edge(*edge)
            if Debug.is_enabled():
                for rule in rules:
                    log_debug("Rejected {}".format(rule))

    @staticmethod
    def _update_bundle_offsets(graph: nx.DiGraph) -> None:
        """Calculate the offsets and store them in the bundles."""
        # Assign inital depths to the nodes.
        nodes = graph.nodes
        for bundle in nodes:
            is_root = True
            for _ in graph.predecessors(bundle):
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
                    for bundle2 in graph.successors(bundle1):
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
        parallel: MutableMapping[Axis, List[_NetworkAndBundle]] = OrderedDict()
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
                    for net_bundle in nbs:
                        bundle = net_bundle[1]
                        bundle.offset = i - mid

    def _overlapping_bundles(
            self,
            net_bundles: Iterable[_NetworkAndBundle]
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
        net_bundles = list(net_bundles)
        graph = nx.Graph()
        for net_bundle in net_bundles:
            bundle = net_bundle[1]
            graph.add_node(bundle, nb=net_bundle)
        for i, net_bundle_1 in enumerate(net_bundles):
            _, bundle_1 = net_bundle_1
            for net_bundle_2 in net_bundles[i + 1:]:
                _, bundle_2 = net_bundle_2
                if self._bundles_overlap(net_bundle_1, net_bundle_2):
                    graph.add_edge(bundle_1, bundle_2)
        for bundles in nx.connected_components(graph):
            block = []
            for bundle in bundles:
                net_bundle = graph.nodes[bundle]['nb']
                block.append(net_bundle)
            yield block

    def _stack_overlapping_bundles(
            self,
            net_bundles: Iterable[_NetworkAndBundle]
    ) -> Sequence[Sequence[_NetworkAndBundle]]:
        """Stack collinear bundles so that they do not overlap."""
        key = lambda net_bundle: net_bundle[1].offset
        net_bundles = sorted(net_bundles, key=key)
        result: List[List[_NetworkAndBundle]] = []
        for net_bundle in net_bundles:
            overlap_on = -1
            n_results = len(result)
            for i in range(n_results - 1, -1, -1):
                row = result[i]
                for net_bundle_2 in row:
                    if self._bundles_overlap(net_bundle, net_bundle_2):
                        overlap_on = i
                        break
                if overlap_on >= 0:
                    break
            if overlap_on == n_results - 1:
                # New row.
                result.append([net_bundle])
            else:
                # Append to existing row.
                result[overlap_on + 1].append(net_bundle)
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
        if vertical and p11.y <= p22.y and p12.y >= p21.y:
            return True
        return False
