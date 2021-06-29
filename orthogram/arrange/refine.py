"""Refine the results of the router."""

from enum import Enum, auto
from itertools import permutations

from typing import (
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
)

from cassowary import SimplexSolver  # type: ignore
from cassowary.error import RequiredFailure  # type: ignore

import networkx as nx  # type: ignore

from ..debug import Debug

from ..geometry import (
    Axis,
    Direction,
    IntPoint,
    Orientation,
)

from ..util import (
    class_str,
    log_debug,
)

from .net import (
    Bundle,
    BundleStructure,
    Network,
    NetworkBundle,
    NetworkOrigin,
    WireSegment,
)

from .route import (
    Route,
    RouteSegment,
    Router,
)

######################################################################

class BundleSegment:
    """Combination of a bundle and one of its segments.

    We need to have this to make rules, because the direction of the
    bundle is *not* the direction of the segment.

    """

    def __init__(self, bundle: Bundle, segment: RouteSegment):
        """Initialize for a given bundle and segment."""
        self._bundle = bundle
        self._segment = segment

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def bundle(self) -> Bundle:
        """The bundle."""
        return self._bundle

    @property
    def segment(self) -> RouteSegment:
        """The segment."""
        return self._segment

    def description(self) -> str:
        """Return a description of the bundle."""
        bundle = self._bundle
        seg = self._segment
        return f"{bundle}, {seg}"

######################################################################

class Passthrough:
    """Passing of a route through a point."""

    def __init__(
            self,
            route: Route,
            point: IntPoint,
            bundle_segment_in: Optional[BundleSegment],
            bundle_segment_out: Optional[BundleSegment],
    ):
        """Initialize for the given bundles interacting at the point."""
        self._route = route
        self._point = point
        self._bundle_segment_in = bundle_segment_in
        self._bundle_segment_out = bundle_segment_out
        self._bundle_bottom: Optional[Bundle] = None
        self._bundle_left: Optional[Bundle] = None
        self._bundle_right: Optional[Bundle] = None
        self._bundle_top: Optional[Bundle] = None
        self._store_bundles()

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def route(self) -> Route:
        """Route passing through the point."""
        return self._route

    @property
    def point(self) -> IntPoint:
        """Point through which the route passes."""
        return self._point

    @property
    def bundle_bottom(self) -> Optional[Bundle]:
        """Bundle at the bottom side."""
        return self._bundle_bottom

    @property
    def bundle_left(self) -> Optional[Bundle]:
        """Bundle at the left side."""
        return self._bundle_left

    @property
    def bundle_right(self) -> Optional[Bundle]:
        """Bundle at the right side."""
        return self._bundle_right

    @property
    def bundle_top(self) -> Optional[Bundle]:
        """Bundle at the top side."""
        return self._bundle_top

    def bundles(self) -> Iterator[Bundle]:
        """Return the bundles passing through the point."""
        bundles = [
            self._bundle_bottom,
            self._bundle_left,
            self._bundle_right,
            self._bundle_top,
        ]
        for bundle in bundles:
            if bundle:
                yield bundle

    def description(self) -> str:
        """Return a description of the object."""
        point = self._point
        i = point.i
        j = point.j
        route = self._route
        return f"{route}, i={i}, j={j}"

    def _store_bundles(self) -> None:
        """Store the bundles in the appropriate place."""
        Dir = Direction
        bottom: Optional[Bundle] = None
        left: Optional[Bundle] = None
        right: Optional[Bundle] = None
        top: Optional[Bundle] = None
        bundle_segment = self._bundle_segment_in
        if bundle_segment:
            bundle = bundle_segment.bundle
            segment = bundle_segment.segment
            direc = segment.direction
            if direc is Dir.DOWN:
                top = bundle
            elif direc is Dir.LEFT:
                right = bundle
            elif direc is Dir.RIGHT:
                left = bundle
            elif direc is Dir.UP:
                bottom = bundle
        bundle_segment = self._bundle_segment_out
        if bundle_segment:
            bundle = bundle_segment.bundle
            segment = bundle_segment.segment
            direc = segment.direction
            if direc is Dir.DOWN:
                bottom = bundle
            elif direc is Dir.LEFT:
                left = bundle
            elif direc is Dir.RIGHT:
                right = bundle
            elif direc is Dir.UP:
                top = bundle
        self._bundle_bottom = bottom
        self._bundle_left = left
        self._bundle_right = right
        self._bundle_top = top

######################################################################

class Interaction:
    """Interaction of two routes at a point."""

    def __init__(
            self,
            point: IntPoint,
            passthroughs: Tuple[Passthrough, Passthrough],
    ):
        """Initialize at the given point for two route passthroughs."""
        self._point = point
        self._passthroughs = passthroughs

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def point(self) -> IntPoint:
        """Grid point at which the interaction happens."""
        return self._point

    @property
    def passthroughs(self) -> Tuple[Passthrough, Passthrough]:
        """The passthroughs of the two routes."""
        return self._passthroughs

    def description(self) -> str:
        """Return a description of the object."""
        passthroughs = self._passthroughs
        route_1 = passthroughs[0].route
        route_2 = passthroughs[1].route
        point = self._point
        i = point.i
        j = point.j
        return f"{route_1}, {route_2}, i={i}, j={j}"

######################################################################

class RuleCategory(Enum):
    """Types of rules."""
    T = auto()
    V = auto()
    S = auto()

######################################################################

class BundleRule:
    """Declares that one bundle comes after another."""

    def __init__(
            self,
            category: RuleCategory,
            first: Bundle, second: Bundle,
    ):
        """Initialize the rule between the two bundles."""
        # Ensure that the two bundles are collinear.
        assert first.orientation is second.orientation
        self._category = category
        self._first = first
        self._second = second

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def category(self) -> RuleCategory:
        """Type of rule."""
        return self._category

    @property
    def first(self) -> Bundle:
        """Bundle that comes first."""
        return self._first

    @property
    def second(self) -> Bundle:
        """Bundle that comes second."""
        return self._second

    def description(self) -> str:
        """Return a description of the rule."""
        cat = repr(self._category.name)
        if self.first.orientation is Orientation.HORIZONTAL:
            adverb = "OVER"
        else:
            adverb = "LEFT OF"
        str1 = self._first
        str2 = self._second
        return f"{cat}, {str1} *{adverb}* {str2}"

######################################################################

# This is the type of factory functions that create bundle rules for a
# predefined rule category.
BundleRuleFactory = Callable[[Bundle, Bundle], BundleRule]

def _bundle_rule_factory(category: RuleCategory) -> BundleRuleFactory:
    """Return a function that creates bundle rules of the given category."""
    def factory(
            first: Bundle, second: Bundle,
            category: RuleCategory = category,
    ) -> BundleRule:
        return BundleRule(category, first, second)
    return factory

######################################################################

class Refiner:
    """Used to refine the coarse results of the router."""

    def __init__(self, router: Router):
        """Initialize the refiner for the given router."""
        self._router = router
        self._networks = self._make_networks()
        self._bundle_segments = self._make_bundle_segments()
        self._init_bundle_offsets()
        # Caution: first pass of offset calculation must be completed
        # before calculating the structures!
        self._bundle_structures = self._make_bundle_structures()

    @property
    def router(self) -> Router:
        """The router whose results this object refines."""
        return self._router

    def networks(self) -> Iterator[Network]:
        """Iterate over the calculated networks."""
        yield from self._networks

    def bundle_structures(self) -> Iterator[BundleStructure]:
        """Iterate over the bundle structures."""
        yield from self._bundle_structures

    def segment_intersections(self, segment: WireSegment) -> List[int]:
        """Return the intersections of the segment with other segments."""
        intersections = set()
        for other in self._wire_segments():
            if other is not segment:
                cut = segment.cut_by(other)
                if cut:
                    intersections.add(cut)
        return sorted(intersections)

    def _make_networks(self) -> List[Network]:
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
        nets: List[Network] = []
        for key, group_routes in per_group.items():
            net = Network(*key, group_routes)
            self._set_joint_nodes(net)
            nets.append(net)
        return nets

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

    def _make_bundle_segments(self) -> Dict[RouteSegment, BundleSegment]:
        """Map each route segment to the bundle to which it belongs."""
        result: Dict[RouteSegment, BundleSegment] = {}
        for bundle in self._bundles():
            for seg in bundle.route_segments():
                result[seg] = BundleSegment(bundle, seg)
        return result

    def _init_bundle_offsets(self) -> None:
        """Calculate the initial offsets of the bundles.

        This method uses a constraint solver to calculate the initial
        values for the offsets of the bundles.  It stores the results
        in the bundles themselves.

        The calculated values are not final!  The bundles should be
        structured into layers to attain their final offsets.

        """
        solver = SimplexSolver()
        tv_rules: List[BundleRule] = []
        s_rules: List[List[BundleRule]] = []
        for inter in self._interactions():
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
            self._try_add_rules_to_solver(solver, [rule])
        for rules in s_rules:
            self._try_add_rules_to_solver(solver, rules)

    def _interactions(self) -> Iterator[Interaction]:
        """Iterate over the interactions of the routes at each point."""
        # Collect the passthroughs at each point.
        per_point: Dict[IntPoint, List[Passthrough]] = {}
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
                inter = Interaction(point, (passthrough_1, passthrough_2))
                yield inter

    def _passthroughs(self, route: Route) -> Iterator[Passthrough]:
        """Iterate over the points through which the route passes."""
        bundle_segments = self._bundle_segments
        seg1: Optional[RouteSegment] = None
        bseg1: Optional[BundleSegment] = None
        for seg2 in route.segments():
            bseg2 = bundle_segments[seg2]
            points = list(seg2.through_points())
            n_points = len(points)
            for i in range(n_points - 1):
                point = points[i]
                yield Passthrough(
                    route=route,
                    point=point,
                    bundle_segment_in=bseg1,
                    bundle_segment_out=bseg2,
                )
                # Set previous segment for each point.
                seg1 = seg2
                bseg1 = bundle_segments[seg1]
        # Last point of route.
        if seg1 and bseg1:
            points = list(seg1.through_points())
            yield Passthrough(
                route=route,
                point=points[-1],
                bundle_segment_in=bseg1,
                bundle_segment_out=None,
            )

    @staticmethod
    def _t_rule(
            passthrough_1: Passthrough,
            passthrough_2: Passthrough
    ) -> Optional[BundleRule]:
        """Rule between bundles for the T-junction interaction.

        The two routes interact like this:

        --+--
          |
          |

        """
        bot_1 = passthrough_1.bundle_bottom
        lef_1 = passthrough_1.bundle_left
        rig_1 = passthrough_1.bundle_right
        top_1 = passthrough_1.bundle_top
        bot_2 = passthrough_2.bundle_bottom
        lef_2 = passthrough_2.bundle_left
        rig_2 = passthrough_2.bundle_right
        top_2 = passthrough_2.bundle_top
        make = _bundle_rule_factory(RuleCategory.T)
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
            passthrough_1: Passthrough,
            passthrough_2: Passthrough
    ) -> List[BundleRule]:
        """Rules for the vertex-to-vertex interaction.

        The two routes interact at a single point, like this:

          |
        --'
           ,--
           |

        The method returns two rules for each case; *either* one of
        them will do.

        """
        bot_1 = passthrough_1.bundle_bottom
        lef_1 = passthrough_1.bundle_left
        rig_1 = passthrough_1.bundle_right
        lef_2 = passthrough_2.bundle_left
        rig_2 = passthrough_2.bundle_right
        top_2 = passthrough_2.bundle_top
        make = _bundle_rule_factory(RuleCategory.V)
        if bot_1 and lef_1 and rig_2 and top_2:
            return [make(bot_1, top_2), make(rig_2, lef_1)]
        if bot_1 and rig_1 and lef_2 and top_2:
            return [make(lef_2, rig_1), make(top_2, bot_1)]
        return []

    @staticmethod
    def _s_rules(
            passthrough_1: Passthrough,
            passthrough_2: Passthrough
    ) -> List[List[BundleRule]]:
        """Rules for the "spoon" interaction.

        The two routes interact like this:

        ||
        |`--
        `---

        This method returns *pairs* of rules; either both rules of a
        pair must be added to the DAG or neither.  However, either
        pair will do.

        """
        bot_1 = passthrough_1.bundle_bottom
        lef_1 = passthrough_1.bundle_left
        rig_1 = passthrough_1.bundle_right
        top_1 = passthrough_1.bundle_top
        bot_2 = passthrough_2.bundle_bottom
        lef_2 = passthrough_2.bundle_left
        rig_2 = passthrough_2.bundle_right
        top_2 = passthrough_2.bundle_top
        make = _bundle_rule_factory(RuleCategory.S)
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

    @staticmethod
    def _try_add_rules_to_solver(
            solver: SimplexSolver,
            rules: List[BundleRule],
    ) -> None:
        """Try to add the rules as constraints to the solver.

        It rolls back all the rules if one of them leads to an
        infeasible constraint.

        """
        added = []
        success = True
        for rule in rules:
            bundle1 = rule.first
            bundle2 = rule.second
            # Do not use the bundle against itself!
            if bundle1 is bundle2:
                continue
            constraint = bundle2.offset_var >= bundle1.offset_var + 1
            try:
                solver.add_constraint(constraint)
                added.append(constraint)
            except RequiredFailure:
                # Abort if the latest constraint is infeasible.
                success = False
                break
        if success:
            if Debug.is_enabled():
                for rule in rules:
                    log_debug(f"Added {rule}")
        else:
            # Remove the constraints if one of them proved infeasible.
            for constraint in added:
                solver.remove_constraint(constraint)
            if Debug.is_enabled():
                for rule in rules:
                    log_debug(f"Rejected {rule}")

    def _make_bundle_structures(self) -> List[BundleStructure]:
        """Group the bundles in collections of overlapping bundles.

        This has the side effect of updating the offsets of the
        bundles!

        """
        result: List[BundleStructure] = []
        by_axis = self._bundles_by_axis()
        for axis, axis_nbs in by_axis.items():
            structs: List[BundleStructure] = []
            for over_nbs in self._overlapping_bundles(axis_nbs):
                index = len(structs)
                struct = BundleStructure(axis, index, over_nbs)
                # This updates the offsets of the bundles!
                struct.restructure()
                structs.append(struct)
                result.extend(structs)
        return result

    def _bundles_by_axis(self) -> Dict[Axis, List[NetworkBundle]]:
        """Group the bundles by grid axis."""
        result: Dict[Axis, List[NetworkBundle]] = {}
        for net in self._networks:
            for bundle in net.bundles():
                axis = bundle.axis
                if not axis in result:
                    result[axis] = []
                net_bundle = NetworkBundle(net, bundle)
                result[axis].append(net_bundle)
        return result

    @staticmethod
    def _overlapping_bundles(
            net_bundles: Iterable[NetworkBundle]
    ) -> Iterator[List[NetworkBundle]]:
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
            bundle = net_bundle.bundle
            graph.add_node(bundle, nb=net_bundle)
        for i, net_bundle_1 in enumerate(net_bundles):
            bundle_1 = net_bundle_1.bundle
            for net_bundle_2 in net_bundles[i + 1:]:
                bundle_2 = net_bundle_2.bundle
                # Caution: To create the structures, we do *not* take
                # into account the offsets when checking for overlap!
                if net_bundle_1.overlaps_with(net_bundle_2, False):
                    graph.add_edge(bundle_1, bundle_2)
        for bundles in nx.connected_components(graph):
            block = []
            for bundle in bundles:
                net_bundle = graph.nodes[bundle]['nb']
                block.append(net_bundle)
            yield block

    def _wire_segments(self) -> Iterator[WireSegment]:
        """Return the wire segments."""
        for net in self._networks:
            for wire in net.wires():
                yield from wire.segments()

    def _bundles(self) -> Iterator[Bundle]:
        """Return the bundles."""
        for net in self._networks:
            yield from net.bundles()
