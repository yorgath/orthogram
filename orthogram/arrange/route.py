"""Route connections between diagram blocks."""

from collections import OrderedDict

from typing import (
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import networkx as nx # type: ignore

from ..define import (
    Block,
    Connection,
    Diagram,
    Node,
    Side,
    TextOrientation,
)

from ..geometry import (
    Axis,
    IntBounds,
    IntPoint,
    Orientation,
    OrientedVector,
)

from ..util import log_warning

######################################################################

# Iterator of nodes and their positions in the layout grid.
_NodesAndPointsIterator = Iterator[Tuple[Node, IntPoint]]

# Iterator of layout grid points and nodes.
_PointsAndNodesIterator = Iterator[Tuple[IntPoint, Optional[Node]]]

######################################################################

class _LayoutCell:
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
        self._rows: List[List[_LayoutCell]]
        self._node_points: MutableMapping[Node, IntPoint]
        self._init_rows(diagram)

    def  __repr__(self) -> str:
        """Convert to string."""
        return "{}(height={}, width={})".format(
            self.__class__.__name__,
            self._height,
            self._width,
        )

    @property
    def height(self) -> int:
        """Number of grid rows."""
        return self._height

    @property
    def width(self) -> int:
        """Number of grid columns."""
        return self._width

    def cell_at(self, point: IntPoint) -> _LayoutCell:
        """Return the cell at the given grid point."""
        return self._rows[point.i][point.j]

    def node_point(self, node: Node) -> IntPoint:
        """Return the position of the node in the layout grid."""
        return self._node_points[node]

    def points_and_nodes(self) -> _PointsAndNodesIterator:
        """Return an iterator over the points and associated nodes."""
        for i, row in enumerate(self._rows):
            for j, cell in enumerate(row):
                point = IntPoint(i, j)
                yield point, cell.node

    def block_bounds(self, block: Block) -> Optional[IntBounds]:
        """Calculate the bounding box of a block on the grid.

        Returns None if the block is not placed in the grid.

        """
        bounds: Optional[IntBounds] = None
        for point in self.block_points(block):
            if not bounds:
                i = point.i
                j = point.j
                bounds = IntBounds(imin=i, jmin=j, imax=i, jmax=j)
            else:
                bounds.expand_to(point)
        return bounds

    def block_points(self, block: Block) -> Iterator[IntPoint]:
        """Return an iterator over the points covered by the block.

        This includes the layout points between the nodes.

        """
        dia_bounds = block.bounds
        if dia_bounds:
            dia_point_1 = IntPoint(dia_bounds.imin, dia_bounds.jmin)
            lay_point_1 = self._diagram_to_layout(dia_point_1)
            dia_point_2 = IntPoint(dia_bounds.imax, dia_bounds.jmax)
            lay_point_2 = self._diagram_to_layout(dia_point_2)
            for i in range(lay_point_1.i, lay_point_2.i + 1):
                for j in range(lay_point_1.j, lay_point_2.j + 1):
                    yield IntPoint(i, j)

    def edges(self) -> Iterator[Tuple[IntPoint, IntPoint]]:
        """Return an iterator over all the edges of the grid."""
        height = self._height
        width = self._width
        for i in range(height):
            for j in range(width):
                point_1 = IntPoint(i, j)
                if j < width - 1:
                    point_2 = IntPoint(i, j + 1)
                    yield point_1, point_2
                if i < height - 1:
                    point_2 = IntPoint(i + 1, j)
                    yield point_1, point_2

    @staticmethod
    def axis(orientation: Orientation, coord: int) -> Axis:
        """Return an axis of the grid."""
        return Axis(orientation, coord)

    def _init_rows(self, diagram: Diagram) -> None:
        """Create the cells of the grid."""
        # Create an empty grid first.
        rows = []
        for _ in range(self._height):
            row: List[_LayoutCell] = []
            for _ in range(self._width):
                cell = _LayoutCell()
                row.append(cell)
            rows.append(row)
        # Now put the nodes into the cells.
        node_points = OrderedDict()
        for node, blocks in diagram.nodes_and_blocks():
            diagram_point = node.point
            layout_point = self._diagram_to_layout(diagram_point)
            cell = _LayoutCell(node, blocks)
            rows[layout_point.i][layout_point.j] = cell
            node_points[node] = layout_point
        self._rows = rows
        self._node_points = node_points

    @staticmethod
    def _diagram_to_layout(diagram_point: IntPoint) -> IntPoint:
        """Convert diagram coordinates to layout coordinates."""
        i = 2 * diagram_point.i + 1
        j = 2 * diagram_point.j + 1
        return IntPoint(i, j)

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

    @property
    def connection(self) -> Connection:
        """Connection behind the route."""
        return self._connection

    @property
    def label_orientation(self) -> Orientation:
        """Orientation of the label, horizontal of vertical.

        This is derived from the orientation of text in the
        attributes.  If it is FOLLOW, it returns the orientation of
        the segment itself.

        """
        tori = self._connection.attributes.text_orientation
        if tori is TextOrientation.HORIZONTAL:
            return Orientation.HORIZONTAL
        if tori is TextOrientation.VERTICAL:
            return Orientation.VERTICAL
        return self.orientation

    def follows_label(self) -> bool:
        """True if the orientation matches that of the label.

        Segments whose orientation matches the orientation of the wire
        label may be preferable when arranging the labels.

        """
        return self.orientation is self.label_orientation

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

    @property
    def diagram(self) -> Diagram:
        """The diagram for which the router was created."""
        return self._diagram

    @property
    def grid(self) -> LayoutGrid:
        """Layout grid."""
        return self._grid

    def node_at(self, point: IntPoint) -> Optional[Node]:
        """Return the node at the given grid point."""
        return self._grid.cell_at(point).node

    def routes(self) -> Iterator[Route]:
        """Return an iterator over the routes."""
        yield from self._routes

    def segment_map(self) -> Mapping[IntPoint, Iterable[RouteSegment]]:
        """Return a map that maps grid points to the segments on them."""
        result: MutableMapping[IntPoint, List[RouteSegment]] = OrderedDict()
        for route in self._routes:
            for seg in route.segments():
                is_hor = seg.is_horizontal()
                seg_coord = seg.axis.coordinate
                start, end = seg.coordinates
                if start > end:
                    start, end = end, start
                for coord in range(start, end + 1):
                    if is_hor:
                        point = IntPoint(i=seg_coord, j=coord)
                    else:
                        point = IntPoint(i=coord, j=seg_coord)
                    segments = result.get(point)
                    if not segments:
                        segments = []
                        result[point] = segments
                    segments.append(seg)
        return result

    def _init_grid_graph(self) -> None:
        """Initialize the graph of the edges of the grid.

        The initial graph contains only nodes.  The edges are created
        differently for each shortest path run.

        """
        self._grid_graph = graph = nx.Graph()
        grid = self._grid
        for point, node in grid.points_and_nodes():
            graph.add_node(point, node=node)

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
        for node_1 in connection.start.outer_nodes():
            for node_2 in connection.end.outer_nodes():
                path = self._shortest_path_between_nodes(
                    connection, node_1, node_2
                )
                if path:
                    length = self._path_length(path)
                    if shortest_length is None or length < shortest_length:
                        shortest_path = path
                        shortest_length = length
        if not shortest_path:
            msg = "No path between {} and {}".format(
                connection.start.name, connection.end.name)
            log_warning(msg)
            return []
        return shortest_path

    def _shortest_path_between_nodes(
            self,
            connection: Connection,
            start: Node, end: Node
    ) -> Optional[List[IntPoint]]:
        """Calculate the shortest path between two nodes.

        Returns the points through which the path passes.  Returns
        None if there is no path between the nodes.

        """
        forbidden = self._forbidden_points(start, end)
        grid = self._grid
        point_1 = grid.node_point(start)
        point_2 = grid.node_point(end)
        graph = self._grid_graph
        # Connect the nodes to form a grid, except the ones through
        # which the connection is not allowed to pass.  We need to
        # clear the edges of the previous run first.
        graph.clear_edges()
        for point_a, point_b in grid.edges():
            # Check for blocking blocks.
            if point_a not in forbidden and point_b not in forbidden:
                if self._must_create_edge(
                        connection, (start, end), (point_a, point_b)
                ):
                    weight = self._edge_weight(
                        connection, (point_1, point_2), (point_a, point_b)
                    )
                    graph.add_edge(point_a, point_b, weight=weight)
        path = nx.shortest_path(graph, point_1, point_2, weight='weight')
        if not path:
            return None
        return list(path)

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

    def _must_create_edge(
            self,
            connection: Connection,
            end_nodes: Tuple[Node, Node],
            edge_points: Tuple[IntPoint, IntPoint],
    ) -> bool:
        """Answer whether we must create an edge between two nodes."""
        start, end = end_nodes
        grid = self._grid
        node_a = grid.cell_at(edge_points[0]).node
        node_b = grid.cell_at(edge_points[1]).node
        attrs = connection.attributes
        exits = attrs.exits
        entrances = attrs.entrances
        result = True
        if edge_points[0].i == edge_points[1].i:
            if Side.LEFT not in exits and node_b is start:
                result = False
            elif Side.RIGHT not in exits and node_a is start:
                result = False
            elif Side.LEFT not in entrances and node_b is end:
                result = False
            elif Side.RIGHT not in entrances and node_a is end:
                result = False
        else:
            if Side.TOP not in exits and node_b is start:
                result = False
            elif Side.BOTTOM not in exits and node_a is start:
                result = False
            elif Side.TOP not in entrances and node_b is end:
                result = False
            elif Side.BOTTOM not in entrances and node_a is end:
                result = False
        return result

    @staticmethod
    def _edge_weight(
            connection: Connection,
            end_points: Tuple[IntPoint, IntPoint],
            edge_points: Tuple[IntPoint, IntPoint],
    ) -> float:
        """Calculate a weight for an edge so as to avoid zig-zag lines."""
        start, end = end_points
        point_a, point_b = edge_points
        # Take into account how the connection exits from the source
        # block and enters the destination block.
        attrs = connection.attributes
        exits = attrs.exits
        entrances = attrs.entrances
        # This value is for the "lighter" edges.
        light = 0.9
        # Calculate the weight.  Default is 1.0 ("heavy").
        weight = 1.0
        if point_a.i == point_b.i:
            i = point_a.i
            if Side.LEFT in entrances and i == end.i and point_a.j < end.j:
                weight = light
            elif Side.RIGHT in entrances and i == end.i and point_b.j > end.j:
                weight = light
            elif Side.LEFT in exits and i == start.i and point_a.j < end.j:
                weight = light
            elif Side.RIGHT in exits and i == start.i and point_b.j > end.j:
                weight = light
        else:
            j = point_a.j
            if Side.TOP in entrances and j == end.j and point_a.i < end.i:
                weight = light
            elif Side.BOTTOM in entrances and j == end.j and point_b.i > end.i:
                weight = light
            elif Side.TOP in exits and j == start.j and point_a.i < end.i:
                weight = light
            elif Side.BOTTOM in exits and j == start.j and point_b.i > end.i:
                weight = light
        return weight

    def _path_length(self, path: List[IntPoint]) -> float:
        """Calculate the length of a path in the grid graph."""
        graph = self._grid_graph
        length = 0.0
        for i, point_a in enumerate(path[:-1]):
            point_b = path[i + 1]
            edge = graph.edges[point_a, point_b]
            length += edge['weight']
        return length

    def _make_segments_for_route(
            self,
            points: Sequence[IntPoint],
            connection: Connection,
    ) -> Sequence[RouteSegment]:
        """Generate segments for a route."""
        segments: List[RouteSegment] = []
        seg_points: List[IntPoint] = []
        for point in points:
            count = len(seg_points)
            if count < 2:
                seg_points.append(point)
            else:
                point_1 = seg_points[-2]
                point_2 = seg_points[-1]
                ori_1 = self._points_orientation(point_1, point_2)
                ori_2 = self._points_orientation(point_2, point)
                if ori_1 is ori_2:
                    seg_points.append(point)
                else:
                    seg = self._make_segment_for_route(
                        seg_points[0], point_2,
                        connection,
                    )
                    segments.append(seg)
                    seg_points = [point_2, point]
        # Last segment.
        seg = self._make_segment_for_route(
            seg_points[0], seg_points[-1],
            connection,
        )
        segments.append(seg)
        return segments

    def _make_segment_for_route(
            self,
            point_1: IntPoint, point_2: IntPoint,
            connection: Connection,
    ) -> RouteSegment:
        """Create a new segment for a route."""
        ori = self._points_orientation(point_1, point_2)
        if ori is Orientation.HORIZONTAL:
            axis_coord = point_1.i
            coord_1, coord_2 = point_1.j, point_2.j
        else:
            axis_coord = point_1.j
            coord_1, coord_2 = point_1.i, point_2.i
        axis = self._grid.axis(ori, axis_coord)
        return RouteSegment(connection, axis, coord_1, coord_2)

    @staticmethod
    def _points_orientation(
            point_1: IntPoint, point_2: IntPoint
    ) -> Orientation:
        """Orientation of the segment formed by the two points."""
        if point_1.i == point_2.i:
            return Orientation.HORIZONTAL
        return Orientation.VERTICAL
