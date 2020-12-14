"""Route links between diagram terminals."""

from enum import Enum, auto

from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import igraph # type: ignore

from .diagram import (
    Cell,
    Diagram,
    Link,
    Pin,
)

from .geometry import (
    Axis,
    IntPoint,
    Orientation,
    OrientedVector,
)

######################################################################

# Iterator of terminal pins and their positions in the layout grid.
PinsAndPointsIterator = Iterator[Tuple[Pin, IntPoint]]

# Iterator of grid points and placed terminal pins.
PointsAndPinsIterator = Iterator[Tuple[IntPoint, Optional[Pin]]]

######################################################################

class AxisLocation(Enum):
    """Location of a grid axis relative to the pins in the diagram."""
    COLUMN_BETWEEN_PINS = auto()
    OUTER_COLUMN = auto()
    OUTER_ROW = auto()
    OVER_PINS = auto()
    ROW_BETWEEN_PINS = auto()

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
        """Location of the axis relative to the pins."""
        return self._location

######################################################################

class LayoutGrid:
    """Layout grid."""

    def __init__(self, diagram: Diagram):
        """Initialize for the given diagram."""
        #
        self._height = 2 * diagram.n_rows() + 1
        self._width = 2 * diagram.max_row() + 1
        self._rows: List[List[Cell]]
        self._pin_points: Dict[Pin, IntPoint]
        self._forbidden_points: Set[IntPoint]
        #
        self._init_rows(diagram)
        self._collect_forbidden_points()

    def  __repr__(self) -> str:
        """Convert to string."""
        return "{}(height={}, width={})".format(
            self.__class__.__name__,
            self._height,
            self._width,
        )

    def _init_rows(self, diagram: Diagram) -> None:
        """Create the cells of the grid."""
        # Create an empty grid first.
        g_rows = []
        for _ in range(self._height):
            g_row: List[Cell] = []
            for _ in range(self._width):
                cell = Cell()
                g_row.append(cell)
            g_rows.append(g_row)
        # Now put the pins into the cells.
        pps = {}
        for di, d_row in enumerate(diagram.rows()):
            for dj, cell in enumerate(d_row):
                dp = IntPoint(di, dj)
                gp = self._diagram_to_grid(dp)
                gi, gj = gp.i, gp.j
                g_rows[gi][gj] = cell
                pin = cell.pin
                if pin:
                    pps[pin] = gp
        self._rows = g_rows
        self._pin_points = pps

    def _collect_forbidden_points(self) -> None:
        """Find the points between pins of the same terminal.

        We do not want the router to go through these points.

        """
        forbidden: Set[IntPoint] = set()
        rows = self._rows
        for i in range(0, self._height - 2):
            for j in range(0, self._width - 2):
                t1 = rows[i][j].terminal
                if t1:
                    t2 = rows[i][j + 2].terminal
                    if t1 is t2:
                        p = IntPoint(i, j + 1)
                        forbidden.add(p)
                    t2 = rows[i + 2][j].terminal
                    if t1 is t2:
                        p = IntPoint(i + 1, j)
                        forbidden.add(p)
        self._forbidden_points = forbidden

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
        i = 2 * p.i + 1
        j = 2 * p.j + 1
        return IntPoint(i, j)

    def cell_at(self, p: IntPoint) -> Cell:
        """Return the cell at the given grid point."""
        return self._rows[p.i][p.j]

    def pin_point(self, pin: Pin) -> IntPoint:
        """Return the position of the pin in the grid."""
        return self._pin_points[pin]

    def pins_and_points(self) -> PinsAndPointsIterator:
        """Return an iterator over the terminal pins and their positions."""
        yield from self._pin_points.items()

    def points_and_pins(self) -> PointsAndPinsIterator:
        """Return an iterator over the points and associated pins."""
        for i, row in enumerate(self._rows):
            for j, cell in enumerate(row):
                p = IntPoint(i, j)
                yield p, cell.pin

    def permitted_edges(self) -> Iterator[Tuple[IntPoint, IntPoint]]:
        """Return an iterator over the edges that one can follow."""
        forbidden = self._forbidden_points
        for p1, p2 in self._edges():
            if p1 not in forbidden and p2 not in forbidden:
                yield p1, p2

    def _edges(self) -> Iterator[Tuple[IntPoint, IntPoint]]:
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
        """Return the location of the given axis relative to the pins."""
        height, width = self._height, self._width
        if orientation is Orientation.HORIZONTAL:
            if coord == 0 or coord == height - 1 :
                return AxisLocation.OUTER_ROW
            elif coord % 2 == 1:
                return AxisLocation.OVER_PINS
            else:
                return AxisLocation.ROW_BETWEEN_PINS
        else:
            if coord == 0 or coord == width - 1:
                return AxisLocation.OUTER_COLUMN
            elif coord % 2 == 1:
                return AxisLocation.OVER_PINS
            else:
                return AxisLocation.COLUMN_BETWEEN_PINS

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

    def __init__(
            self,
            name: str,
            link: Link,
            axis: LayoutAxis,
            c1: int, c2: int,
    ):
        """Initialize the segment.

        The name of the segment must be unique among *all* the
        segments of the diagram, because it is used as a key in
        graphs.

        """
        self._name = name
        self._link = link
        self._axis = axis
        self._coords = (c1, c2)

    def __repr__(self) -> str:
        """Convert to string."""
        coords = self._coords
        return "{}({}; {}; {}; {}->{})".format(
            self.__class__.__name__,
            self._name,
            self._link,
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
    """Path between two terminals."""

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
    """Calculates the routes between the linked terminals of a diagram."""

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
        for p, n in grid.points_and_pins():
            graph.add_vertex(p.name(), point=p, pin=n)

    def _init_routes(self) -> None:
        """Create the routes for all the links of the diagram."""
        routes: List[Route] = []
        for link in self._diagram.links():
            name = "R{}".format(len(routes))
            route = self._make_route(name, link)
            routes.append(route)
        self._routes = routes

    def _make_route(self, name: str, link: Link) -> Route:
        """Create the route between two terminal pins."""
        points = self._shortest_path_of_link(link)
        prefix = "{}.".format(name)
        segments = self._make_segments_for_route(prefix, points, link)
        return Route(name, link, segments)

    def _shortest_path_of_link(self, link: Link) -> Sequence[IntPoint]:
        """Calculate the shortest path between the two link terminals.

        Returns the points through which the path passes.

        """
        shortest_path: Optional[List[IntPoint]] = None
        shortest_length: Optional[float] = None
        for n1 in link.start.pins():
            for n2 in link.end.pins():
                path, length = self._shortest_path_between_pins(link, n1, n2)
                if shortest_length is None or length < shortest_length:
                    shortest_path = path
                    shortest_length = length
        assert shortest_path
        return shortest_path

    def _shortest_path_between_pins(
            self,
            link: Link,
            n1: Pin, n2: Pin
    ) -> Tuple[List[IntPoint], float]:
        """Calculate the shortest path between two terminal pins.

        Returns the points through which the path passes and the
        length of the path.

        """
        bias_s = 0.9
        bias_l = 0.8
        attrs = link.attributes
        b1 = attrs.start_bias
        b2 = attrs.end_bias
        hor = Orientation.HORIZONTAL
        ver = Orientation.VERTICAL
        grid = self._grid
        p1 = grid.pin_point(n1)
        p2 = grid.pin_point(n2)
        graph = self._grid_graph
        # Connect the vertices to form a grid, except the ones leading
        # to other pins.  We need to clear the edges of the previous
        # run first.
        graph.delete_edges()
        for pa, pb in grid.permitted_edges():
            ca = grid.cell_at(pa)
            ta, na = ca.terminal, ca.pin
            na = ca.pin
            cb = grid.cell_at(pb)
            tb, nb = cb.terminal, cb.pin
            # Do not connect vertices of foreign pins!
            if ((na is None or na is n1 or na is n2) and
                (nb is None or nb is n1 or nb is n2)):
                # Give an appropriate weight to the edge
                # for aesthetic reasons mainly.
                weight = 1.0
                if pa.i == pb.i:
                    if b1 is hor:
                        if na is n1 or nb is n1:
                            weight = bias_l
                        elif pa.i == p1.i or pb.i == p1.i:
                            weight = bias_s
                    if b2 is hor:
                        if na is n2 or nb is n2:
                            weight = bias_l
                        elif pa.i == p2.i or pb.i == p2.i:
                            weight = bias_s
                elif pa.j == pb.j:
                    if b1 is ver:
                        if na is n1 or nb is n1:
                            weight = bias_l
                        elif pa.j == p1.j or pb.j == p1.j:
                            weight = bias_s
                    if b2 is ver:
                        if na is n2 or nb is n2:
                            weight = bias_l
                        elif pa.j == p2.j or pb.j == p2.j:
                            weight = bias_s
                graph.add_edge(pa.name(), pb.name(), weight=weight)
        paths = graph.get_shortest_paths(
            p1.name(), p2.name(),
            weights='weight',
        )
        assert paths
        path = paths[0]
        assert path
        # The path consists of vertices.  Collect the points.
        points: List[IntPoint] = []
        for idx in path:
            v = graph.vs[idx]
            points.append(v['point'])
        # Calculate the length of the path.
        length = 0.0
        for i, idx1 in enumerate(path[:-1]):
            idx2 = path[i + 1]
            eid = graph.get_eid(idx1, idx2)
            e = graph.es[eid]
            length += e['weight']
        return points, length

    def _make_segments_for_route(
            self,
            prefix: str,
            points: Sequence[IntPoint],
            link: Link,
    ) -> Sequence[RouteSegment]:
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
                        link,
                    )
                    segments.append(seg)
                    seg_points = [p2, p]
        # Last segment.
        seg = self._make_segment_for_route(
            prefix,
            len(segments),
            seg_points[0], seg_points[-1],
            link,
        )
        segments.append(seg)
        return segments

    def _make_segment_for_route(
            self,
            prefix: str,
            index: int,
            p1: IntPoint, p2: IntPoint,
            link: Link,
    ) -> RouteSegment:
        """Create a new segment for a route."""
        ori = self._points_orientation(p1, p2)
        if ori is Orientation.HORIZONTAL:
            axis_coord = p1.i
            c1, c2 = p1.j, p2.j
        else:
            axis_coord = p1.j
            c1, c2 = p1.i, p2.i
        axis = self._grid.axis(ori, axis_coord)
        name = "{}{}".format(prefix, index)
        return RouteSegment(name, link, axis, c1, c2)

    @staticmethod
    def _points_orientation(p1: IntPoint, p2: IntPoint) -> Orientation:
        """Orientation of the segment formed by the two points."""
        if p1.i == p2.i:
            return Orientation.HORIZONTAL
        else:
            return Orientation.VERTICAL

    @property
    def diagram(self) -> Diagram:
        """The diagram for which the router was created."""
        return self._diagram

    @property
    def grid(self) -> LayoutGrid:
        """Layout grid."""
        return self._grid

    def pin_at(self, p: IntPoint) -> Optional[Pin]:
        """Return the terminal pin at the given grid point."""
        return self._grid.cell_at(p).pin

    def pins_and_points(self) -> PinsAndPointsIterator:
        """Return an iterator over the pins and their grid positions."""
        yield from self.grid.pins_and_points()

    def routes(self) -> Iterator[Route]:
        """Return an iterator over the routes."""
        yield from self._routes
