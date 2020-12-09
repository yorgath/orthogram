"""Route connectors between diagram nodes."""

from enum import Enum, auto

from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

import igraph # type: ignore

from .geometry import (
    Axis,
    Direction,
    IntPoint,
    Orientation,
    OrientedVector,
)

from .diagram import (
    Diagram,
    Link,
    Node,
)

######################################################################

# Iterator of diagram nodes and their positions in the layout grid.
NodesAndPointsIterator = Iterator[Tuple[Node, IntPoint]]

# Iterator of grid points and placed diagram nodes.
_PointsAndNodesIterator = Iterator[Tuple[IntPoint, Optional[Node]]]

######################################################################

class AxisLocation(Enum):
    """Location of a grid axis relative to the nodes of the diagram."""
    COLUMN_BETWEEN_NODES = auto()
    OUTER_COLUMN = auto()
    OUTER_ROW = auto()
    OVER_NODES = auto()
    ROW_BETWEEN_NODES = auto()

######################################################################

class LayoutAxis(Axis):
    """Axis of the layout grid."""

    def __init__(
            self,
            orientation: Orientation,
            coord: int, location:
            AxisLocation
    ):
        """Initialize axis for a given layout location."""
        Axis.__init__(self, orientation, coord)
        self._location = location

    @property
    def location(self) -> AxisLocation:
        """Location of the axis relative to the nodes."""
        return self._location
    
######################################################################

class LayoutGrid:
    """Layout grid."""

    def __init__(self, diagram: Diagram):
        """Initialize for the given diagram."""
        #
        self._height: int
        self._width: int
        self._row_min: int
        self._row_max: int
        self._node_min: int
        self._node_max: int
        self._rows: List[List[Optional[Node]]]
        self._node_points: Dict[Node, IntPoint]
        #
        self._calculate_dimensions(diagram)
        self._create_rows(diagram)
        
    def  __repr__(self) -> str:
        """Convert to string."""
        values = [
            ("height", self._height),
            ("width", self._width),
            ("row_min", self._row_min),
            ("row_max", self._row_max),
            ("node_min", self._node_min),
            ("node_max", self._node_max),
        ]
        strings = []
        for k, v in values:
            a = "{}={}".format(k, v)
            strings.append(a)
        return "{}({})".format(
            self.__class__.__name__,
            ",".join(strings),
        )

    def _calculate_dimensions(self, diagram: Diagram) -> None:
        """Calculate and store the dimensions of the grid."""
        #
        # If there is only a single row or column, add space around
        # the nodes, so the router can route around them.
        #
        dh = diagram.n_rows()
        if dh == 1:
            self._height = 3
            self._row_min = 1
            self._row_max = 1
        else:
            self._height = 2 * dh - 1
            self._row_min = 0
            self._row_max = self._height - 1
        dw = diagram.max_row()
        if dw == 1:
            self._width = 3
            self._node_min = 1
            self._node_max = 1
        else:
            self._width = 2 * dw - 1
            self._node_min = 0
            self._node_max = self._width - 1
            
    def _create_rows(self, diagram: Diagram) -> None:
        """Create the cells of the grid."""
        # Create an empty grid first.
        g_rows = []
        for _ in range(self._height):
            g_row: List[Optional[Node]] = []
            for _ in range(self._width):
                g_row.append(None)
            g_rows.append(g_row)
        # Now put the nodes into their cells.
        ntp = {}
        for i, d_row in enumerate(diagram.rows()):
            for j, elt in enumerate(d_row):
                dp = IntPoint(i, j)
                gp = self._diagram_to_grid(dp)
                g_rows[gp.i][gp.j] = elt
                if elt:
                    ntp[elt] = gp
        self._rows = g_rows
        self._node_points = ntp

    @property
    def height(self) -> int:
        """Number of grid rows."""
        return self._height

    @property
    def width(self) -> int:
        """Number of grid columns."""
        return self._width

    def _diagram_to_grid(self, p: IntPoint) -> IntPoint:
        """Convert diagram coordinates to grid coordinates."""
        i = self._row_min + 2 * p.i
        j = self._node_min + 2 * p.j
        return IntPoint(i, j)

    def node_at(self, p: IntPoint) -> Optional[Node]:
        """Return the node at the given grid point."""
        return self._rows[p.i][p.j]
    
    def node_point(self, node: Node) -> IntPoint:
        """Return the position of the node in the grid."""
        return self._node_points[node]

    def nodes_and_points(self) -> NodesAndPointsIterator:
        """Return an iterator over the nodes and their positions."""
        yield from self._node_points.items()
    
    def points_and_nodes(self) -> _PointsAndNodesIterator:
        """Return an iterator over the points and associated nodes."""
        for i, row in enumerate(self._rows):
            for j, elt in enumerate(row):
                p = IntPoint(i, j)
                yield p, elt

    def edges(self) -> Iterator[Tuple[IntPoint, IntPoint]]:
        """Return an iterator over all the edges of the grid."""
        h = self._height
        w = self._width
        for i in range(h):
            for j in range(w):
                p1 = IntPoint(i, j)
                if j < w - 1:
                    p2 = IntPoint(i, j + 1)
                    yield p1, p2
                if i < h - 1:
                    p2 = IntPoint(i + 1, j)
                    yield p1, p2

    def axis(self, orientation: Orientation, coord: int) -> LayoutAxis:
        """Return an axis of the grid."""
        loc = self._axis_location(orientation, coord)
        return LayoutAxis(orientation, coord, loc)
        
    def _axis_location(
            self,
            orientation: Orientation,
            coord: int
    ) -> AxisLocation:
        """Return the location of the given axis relative to the nodes."""
        row_min = self._row_min
        row_max = self._row_max
        node_min = self._node_min
        node_max = self._node_max
        if orientation is Orientation.HORIZONTAL:
            if coord < row_min or coord > row_max:
                return AxisLocation.OUTER_ROW
            elif (coord - row_min) % 2 == 0:
                return AxisLocation.OVER_NODES
            else:
                return AxisLocation.ROW_BETWEEN_NODES
        else:
            if coord < node_min or coord > node_max:
                return AxisLocation.OUTER_COLUMN
            elif (coord - node_min) % 2 == 0:
                return AxisLocation.OVER_NODES
            else:
                return AxisLocation.COLUMN_BETWEEN_NODES

    def axes(self) -> Iterator[LayoutAxis]:
        """Return an iterator over the axes of the grid."""
        data = {
            Orientation.HORIZONTAL: self._height,
            Orientation.VERTICAL: self._width,
        }
        for ori, n in data.items():
            for i in range(n):
                yield self.axis(ori, i)

######################################################################

class RouteSegment(OrientedVector):
    """Segment of a route between angles."""

    def __init__(self, name: str, axis: LayoutAxis, c1: int, c2: int):
        """Initialize the segment.

        The name of the segment must be unique among *all* the
        segments of the diagram, because it is used as a key in
        graphs.

        """
        self._name = name
        self._axis = axis
        self._coords = (c1, c2)
    
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
        """A name that identifies the segment."""
        return self._name

    @property
    def axis(self) -> LayoutAxis:
        """Axis on which the segment lies."""
        return self._axis

    @property
    def coordinates(self) -> Tuple[int, int]:
        """First and last coordinates along the axis."""
        return self._coords
            
######################################################################

class Route:
    """Path between two diagram nodes."""

    def __init__(self, name: str, link: Link, segments: Sequence[RouteSegment]):
        """Initialize the route of a link with the given segments.

        The name must be unique among all the routes of the diagram,
        because it is used as a group name when the link does not
        belong to a named group.

        """
        self._name = name
        self._link = link
        self._segments = list(segments)

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({})".format(self.__class__.__name__, self._name)

    @property
    def name(self) -> str:
        """A name that identifies the route."""
        return self._name

    @property
    def link(self) -> Link:
        """Associated diagram link."""
        return self._link

    def segments(self) -> Iterator[RouteSegment]:
        """Return an iterator over the segments that make up the route."""
        yield from self._segments

######################################################################

class Router:
    """Calculates the routes between the connected nodes of a diagram."""

    def __init__(self, diagram: Diagram):
        """Initialize the router for the given diagram."""
        #
        self._diagram = diagram
        self._grid = LayoutGrid(diagram)
        self._grid_graph: igraph.Graph
        self._routes: List[Route]
        #
        self._init_grid_graph()
        self._init_routes()

    def _init_grid_graph(self) -> None:
        """Initialize the graph of the edges of the grid.

        The initial graph contains only vertices.  The edges are
        created differently for each shortest path run.

        """
        self._grid_graph = graph = igraph.Graph(directed=False)
        grid = self._grid
        for p, elt in grid.points_and_nodes():
            graph.add_vertex(p.name(), point=p, node=elt)
        
    def _init_routes(self) -> None:
        """Create the routes for all the links of the diagram."""
        routes: List[Route] = []
        for link in self._diagram.links():
            name = "R{}".format(len(routes))
            route = self._make_route(name, link)
            routes.append(route)
        self._routes = routes

    def _make_route(self, name: str, link: Link) -> Route:
        """Create the route between two diagram nodes."""
        points = self._shortest_path(link)
        prefix = "{}.".format(name)
        segments = self._make_segments_for_route(prefix, points)
        return Route(name, link, segments)

    def _shortest_path(self, link: Link) -> Sequence[IntPoint]:
        """Calculate the shortest path between the two nodes of the link.

        Returns the points through which the path passes.

        """
        n1 = link.start
        n2 = link.end
        attrs = link.attributes
        b1 = attrs.start_bias
        b2 = attrs.end_bias
        hor = Orientation.HORIZONTAL
        ver = Orientation.VERTICAL
        bias_weight = 0.9
        grid = self._grid
        p1 = grid.node_point(n1)
        p2 = grid.node_point(n2)
        graph = self._grid_graph
        # Connect the vertices to form a grid, except the ones leading
        # to other diagram nodes.  We need to clear the edges of the
        # previous run first.
        graph.delete_edges()
        for pa, pb in grid.edges():
            na = grid.node_at(pa)
            nb = grid.node_at(pb)
            # Do not connect vertices of foreign nodes!
            if ((na is None or na is n1 or na is n2) and
                (nb is None or nb is n1 or nb is n2)):
                    # Give an appropriate weight to the edge
                    # for aesthetic reasons mainly.
                    weight = 1.0
                    if pa.i == pb.i:
                        if (n1 is na or n1 is nb) and b1 is hor:
                            weight = bias_weight
                        elif (n2 is na or n2 is nb) and b2 is hor:
                            weight = bias_weight
                    elif pa.j == pb.j:
                        if (n1 is na or n1 is nb) and b1 is ver:
                            weight = bias_weight
                        elif (n2 is na or n2 is nb) and b2 is ver:
                            weight = bias_weight
                    graph.add_edge(pa.name(), pb.name(), weight=weight)
        paths = graph.get_all_shortest_paths(
            p1.name(), p2.name(), weights='weight')
        result: List[IntPoint] = []
        for idx in paths[0]:
            p = graph.vs[idx]['point']
            result.append(p)
        return result

    def _make_segments_for_route(
            self,
            prefix: str,
            points: Sequence[IntPoint]
    ) -> List[RouteSegment]:
        """Generate segments for a route."""
        segments: List[RouteSegment] = []
        seg_points: List[IntPoint] = []
        for p in points:
            n = len(seg_points)
            if n < 2:
                seg_points.append(p)
            else:
                p1 = seg_points[-2]
                p2 = seg_points[-1]
                ori_1 = self._points_orientation(p1, p2)
                ori_2 = self._points_orientation(p2, p)
                if ori_1 is ori_2:
                    seg_points.append(p)
                else:
                    seg = self._make_segment_for_route(
                        prefix,
                        len(segments),
                        seg_points[0], p2,
                    )
                    segments.append(seg)
                    seg_points = [p2, p]
        # Last segment.
        seg = self._make_segment_for_route(
            prefix,
            len(segments),
            seg_points[0], seg_points[-1],
        )
        segments.append(seg)
        return segments

    @staticmethod
    def _points_orientation(p1: IntPoint, p2: IntPoint) -> Orientation:
        """Orientation of the segment formed by the two points."""
        if p1.i == p2.i:
            return Orientation.HORIZONTAL
        else:
            return Orientation.VERTICAL

    def _make_segment_for_route(
            self,
            prefix: str,
            index: int,
            p1: IntPoint, p2: IntPoint
    ) -> RouteSegment:
        """Create a new segment for a route."""
        if p1.i == p2.i:
            ori = Orientation.HORIZONTAL
            axis_coord = p1.i
            c1, c2 = p1.j, p2.j
        else:
            ori = Orientation.VERTICAL
            axis_coord = p1.j
            c1, c2 = p1.i, p2.i
        axis = self._grid.axis(ori, axis_coord)
        name = "{}{}".format(prefix, index)
        return RouteSegment(name, axis, c1, c2)
    
    @property
    def diagram(self) -> Diagram:
        """The diagram for which the router was created."""
        return self._diagram
    
    @property
    def grid(self) -> LayoutGrid:
        """Layout grid."""
        return self._grid

    def node_at(self, p: IntPoint) -> Optional[Node]:
        """Return the node at the given grid point."""
        return self._grid.node_at(p)
    
    def nodes_and_points(self) -> NodesAndPointsIterator:
        """Return an iterator over the nodes and their grid positions."""
        yield from self.grid.nodes_and_points()
    
    def routes(self) -> Iterator[Route]:
        """Return an iterator over the routes."""
        yield from self._routes
