"""Route connections between diagram blocks."""

from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import networkx as nx # type: ignore

from .attributes import Side

from .diagram import (
    Block,
    Connection,
    Diagram,
    Node,
)

from .geometry import (
    Axis,
    IntPoint,
    Orientation,
    OrientedVector,
)

from .util import log_warning

######################################################################

# Iterator of nodes and their positions in the layout grid.
NodesAndPointsIterator = Iterator[Tuple[Node, IntPoint]]

# Iterator of layout grid points and nodes.
PointsAndNodesIterator = Iterator[Tuple[IntPoint, Optional[Node]]]

######################################################################

class LayoutCell:
    """Position in the grid, may hold a node and its connected blocks."""

    def __init__(
            self,
            node: Optional[Node] = None,
            blocks: Iterable[Block] = (),
    ):
        """Initialize with the given contents."""
        self._node = node
        self._blocks = set(blocks)

    @property
    def node(self) -> Optional[Node]:
        """node in this cell."""
        return self._node

    def blocks(self) -> Iterator[Block]:
        """Return an iterator over the blocks that cover the cell."""
        yield from self._blocks

    def has_block(self, block: Block) -> bool:
        """Return true if the block is on this cell."""
        return block in self._blocks

######################################################################

class LayoutGrid:
    """Layout grid."""

    def __init__(self, diagram: Diagram):
        """Initialize for the given diagram."""
        # The dimensions of the layout grid are such that they permit
        # the creation of routes between and also around the
        # blocks.
        diagram_grid = diagram.grid
        self._height = 2 * diagram_grid.height + 1
        self._width = 2 * diagram_grid.width + 1
        self._rows: List[List[LayoutCell]]
        self._node_points: Dict[Node, IntPoint]
        self._init_rows(diagram)

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
        rows = []
        for _ in range(self._height):
            row: List[LayoutCell] = []
            for _ in range(self._width):
                cell = LayoutCell()
                row.append(cell)
            rows.append(row)
        # Now put the nodes into the cells.
        nps = {}
        for node, blocks in diagram.nodes_and_blocks():
            dp = node.point
            lp = self._diagram_to_layout(dp)
            cell = LayoutCell(node, blocks)
            li, lj = lp.i, lp.j
            rows[li][lj] = cell
            nps[node] = lp
        self._rows = rows
        self._node_points = nps

    @property
    def height(self) -> int:
        """Number of grid rows."""
        return self._height

    @property
    def width(self) -> int:
        """Number of grid columns."""
        return self._width

    def _diagram_to_layout(self, p: IntPoint) -> IntPoint:
        """Convert diagram coordinates to layout coordinates."""
        i = 2 * p.i + 1
        j = 2 * p.j + 1
        return IntPoint(i, j)

    def cell_at(self, p: IntPoint) -> LayoutCell:
        """Return the cell at the given grid point."""
        return self._rows[p.i][p.j]

    def node_point(self, node: Node) -> IntPoint:
        """Return the position of the node in the layout grid."""
        return self._node_points[node]

    def nodes_and_points(self) -> NodesAndPointsIterator:
        """Return an iterator over the nodes and their positions."""
        yield from self._node_points.items()

    def points_and_nodes(self) -> PointsAndNodesIterator:
        """Return an iterator over the points and associated nodes."""
        for i, row in enumerate(self._rows):
            for j, cell in enumerate(row):
                p = IntPoint(i, j)
                yield p, cell.node

    def block_points(self, block: Block) -> Iterator[IntPoint]:
        """Return an iterator over the points covered by the block.

        This includes the layout points between the nodes.

        """
        db = block.bounds
        if db:
            dp1 = IntPoint(db.imin, db.jmin)
            lp1 = self._diagram_to_layout(dp1)
            dp2 = IntPoint(db.imax, db.jmax)
            lp2 = self._diagram_to_layout(dp2)
            for i in range(lp1.i, lp2.i + 1):
                for j in range(lp1.j, lp2.j + 1):
                    yield IntPoint(i, j)

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

    def axis(self, orientation: Orientation, coord: int) -> Axis:
        """Return an axis of the grid."""
        return Axis(orientation, coord)

    def axes(self) -> Iterator[Axis]:
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

    def __init__(self, connection: Connection, axis: Axis, c1: int, c2: int):
        """Initialize the segment for a given connection."""
        self._connection = connection
        self._axis = axis
        self._coords = (c1, c2)

    def __repr__(self) -> str:
        """Convert to string."""
        coords = self._coords
        return "{}({}; {}; {}->{})".format(
            self.__class__.__name__,
            self._connection,
            self._axis,
            coords[0],
            coords[1],
        )

    @property
    def axis(self) -> Axis:
        """Axis on which the segment lies."""
        return self._axis

    @property
    def coordinates(self) -> Tuple[int, int]:
        """First and last coordinates along the axis."""
        return self._coords

######################################################################

class Route:
    """Path between two blocks."""

    def __init__(
            self,
            name: str,
            connection: Connection,
            segments: Sequence[RouteSegment],
    ):
        """Initialize the route of a connection with the given segments.

        The name must be unique among all the routes of the diagram,
        because it is used as a group name when the connection does
        not belong to a named group.

        """
        self._name = name
        self._connection = connection
        self._segments = list(segments)

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({})".format(self.__class__.__name__, self._name)

    @property
    def name(self) -> str:
        """A name that identifies the route."""
        return self._name

    @property
    def connection(self) -> Connection:
        """Associated diagram connection."""
        return self._connection

    def segments(self) -> Iterator[RouteSegment]:
        """Return an iterator over the segments that make up the route."""
        yield from self._segments

######################################################################

class Router:
    """Calculates the routes between the connected blocks of a diagram."""

    def __init__(self, diagram: Diagram):
        """Initialize the router for the given diagram."""
        self._diagram = diagram
        self._grid = LayoutGrid(diagram)
        self._grid_graph: nx.Graph
        self._init_grid_graph()
        self._routes: List[Route]
        self._init_routes()

    def _init_grid_graph(self) -> None:
        """Initialize the graph of the edges of the grid.

        The initial graph contains only nodes.  The edges are created
        differently for each shortest path run.

        """
        self._grid_graph = graph = nx.Graph()
        grid = self._grid
        for p, n in grid.points_and_nodes():
            graph.add_node(p, node=n)

    def _init_routes(self) -> None:
        """Create the routes for all the connections of the diagram."""
        routes: List[Route] = []
        for connection in self._diagram.connections():
            name = "R{}".format(len(routes))
            route = self._make_route(name, connection)
            if route:
                routes.append(route)
        self._routes = routes

    def _make_route(self, name: str, connection: Connection) -> Optional[Route]:
        """Create the route between two nodes.

        Returns None if it fails to connect the two ends of the
        connection.

        """
        points = self._shortest_path_of_connection(connection)
        if points:
            segments = self._make_segments_for_route(points, connection)
            return Route(name, connection, segments)
        else:
            return None

    def _shortest_path_of_connection(
            self,
            connection: Connection,
    ) -> Sequence[IntPoint]:
        """Calculate the shortest path between the two blocks.

        Returns the points through which the path passes.

        """
        shortest_path: Optional[List[IntPoint]] = None
        shortest_length: Optional[float] = None
        for n1 in connection.start.outer_nodes():
            for n2 in connection.end.outer_nodes():
                result = self._shortest_path_between_nodes(connection, n1, n2)
                if result:
                    path, length = result
                    if shortest_length is None or length < shortest_length:
                        shortest_path = path
                        shortest_length = length
        if not shortest_path:
            msg = "No path between {} and {}".format(
                connection.start.name, connection.end.name)
            log_warning(msg)
            return []
        else:
            return shortest_path

    def _shortest_path_between_nodes(
            self,
            connection: Connection,
            n1: Node, n2: Node
    ) -> Optional[Tuple[List[IntPoint], float]]:
        """Calculate the shortest path between two nodes.

        Returns the points through which the path passes and the
        length of the path.  Returns None if there is no path between
        the nodes.

        """
        heavy = 1.0
        light = 0.9
        attrs = connection.attributes
        entrances = attrs.entrances
        exits = attrs.exits
        forbidden = self._forbidden_points(n1, n2)
        grid = self._grid
        p1 = grid.node_point(n1)
        p2 = grid.node_point(n2)
        graph = self._grid_graph
        # Connect the nodes to form a grid, except the ones through
        # which the connection is not allowed to pass.  We need to
        # clear the edges of the previous run first.
        graph.clear_edges()
        for pa, pb in grid.edges():
            # Check for blocking blocks.
            if pa not in forbidden and pb not in forbidden:
                ca = grid.cell_at(pa)
                na = ca.node
                cb = grid.cell_at(pb)
                nb = cb.node
                # Check side restrictions.
                di = pb.i - pa.i
                dj = pb.j - pa.j
                assert di >= 0 and dj >= 0
                end_bottom = (Side.BOTTOM in entrances)
                end_left = (Side.LEFT in entrances)
                end_right = (Side.RIGHT in entrances)
                end_top = (Side.TOP in entrances)
                start_bottom = (Side.BOTTOM in exits)
                start_left = (Side.LEFT in exits)
                start_right = (Side.RIGHT in exits)
                start_top = (Side.TOP in exits)
                side_ok = True
                if False:
                    pass
                elif not start_top and dj == 0 and nb is n1:
                    side_ok = False
                elif not start_bottom and dj == 0 and na is n1:
                    side_ok = False
                elif not start_left and di == 0 and nb is n1:
                    side_ok = False
                elif not start_right and di == 0 and na is n1:
                    side_ok = False
                elif not end_top and dj == 0 and nb is n2:
                    side_ok = False
                elif not end_bottom and dj == 0 and na is n2:
                    side_ok = False
                elif not end_left and di == 0 and nb is n2:
                    side_ok = False
                elif not end_right and di == 0 and na is n2:
                    side_ok = False
                if side_ok:
                    # Calculate weight so as to avoid zig-zag lines.
                    weight = heavy
                    if di == 0:
                        i = pa.i
                        if False: pass
                        elif end_left and i == p2.i and pa.j < p2.j:
                            weight = light
                        elif end_right and i == p2.i and pb.j > p2.j:
                            weight = light
                        elif start_left and i == p1.i and pa.j < p2.j:
                            weight = light
                        elif start_right and i == p1.i and pb.j > p2.j:
                            weight = light
                    elif dj == 0:
                        j = pa.j
                        if False: pass
                        elif end_bottom and j == p2.j and pb.i > p2.i:
                            weight = light
                        elif end_top and j == p2.j and pa.i < p2.i:
                            weight = light
                        elif start_bottom and j == p1.j and pb.i > p2.i:
                            weight = light
                        elif start_top and j == p1.j and pa.i < p2.i:
                            weight = light
                    graph.add_edge(pa, pb, weight=weight)
        path = nx.shortest_path(graph, p1, p2, weight='weight')
        # Calculate the length of the path.
        length = 0.0
        for i, p1 in enumerate(path[:-1]):
            p2 = path[i + 1]
            e = graph.edges[p1, p2]
            length += e['weight']
        return path, length

    def _forbidden_points(self, start: Node, end: Node) -> Set[IntPoint]:
        """Return the points through which a connection cannot pass.

        All the points covered by blocks are forbidden, except the
        ones of the blocks to which the connection is attached.

        """
        diagram = self._diagram
        grid = self._grid
        # Collect the blocks associated with the connection.
        allowed_blocks = set()
        for node in [start, end]:
            for block in diagram.node_blocks(node):
                allowed_blocks.add(block)
        # Collect the points of all the *other* blocks.
        result: Set[IntPoint] = set()
        for block in diagram.blocks():
            if not (block in allowed_blocks or block.attributes.pass_through):
                result.update(grid.block_points(block))
        return result

    def _make_segments_for_route(
            self,
            points: Sequence[IntPoint],
            connection: Connection,
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
                        len(segments),
                        seg_points[0], p2,
                        connection,
                    )
                    segments.append(seg)
                    seg_points = [p2, p]
        # Last segment.
        seg = self._make_segment_for_route(
            len(segments),
            seg_points[0], seg_points[-1],
            connection,
        )
        segments.append(seg)
        return segments

    def _make_segment_for_route(
            self,
            index: int,
            p1: IntPoint, p2: IntPoint,
            connection: Connection,
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
        return RouteSegment(connection, axis, c1, c2)

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

    def node_at(self, p: IntPoint) -> Optional[Node]:
        """Return the node at the given grid point."""
        return self._grid.cell_at(p).node

    def nodes_and_points(self) -> NodesAndPointsIterator:
        """Return an iterator over the nodes and their grid positions."""
        yield from self.grid.nodes_and_points()

    def node_point(self, node: Node) -> IntPoint:
        """Return the position of the node in the grid."""
        return self._grid.node_point(node)

    def routes(self) -> Iterator[Route]:
        """Return an iterator over the routes."""
        yield from self._routes
