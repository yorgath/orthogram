"""Provides the elements of a diagram."""

from enum import Enum, auto

from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
)

from ..geometry import (
    IntBounds,
    IntPoint,
)

from ..util import (
    class_str,
    grid_str,
    indent,
    log_warning,
    vector_repr,
)

from .attributes import (
    AttributeMap,
    Attributes,
    BlockAttributes,
    ConnectionAttributes,
    DiagramAttributes,
    LabelAttributes,
    TextAttributes,
)

from .defs import (
    BlockDef,
    ConnectionDef,
    DiagramDef,
    SubBlockDef,
)

######################################################################

class ConnectionLabelPosition(Enum):
    """Position of a connection label relative to the connection."""
    START = auto()
    MIDDLE = auto()
    END = auto()

    def is_start(self) -> bool:
        """True if this is at the start of the connection."""
        return self is ConnectionLabelPosition.START

    def is_middle(self) -> bool:
        """True if this is at the middle of the connection."""
        return self is ConnectionLabelPosition.MIDDLE

    def is_end(self) -> bool:
        """True if this is at the end of the connection."""
        return self is ConnectionLabelPosition.END

######################################################################

class DiagramCell:
    """Position in the diagram grid."""

    def __init__(self, point: IntPoint, tag: Optional[str] = None):
        """Initialize for the given point with an optional tag."""
        self._point = point
        # Empty string is not a tag.
        if not tag:
            tag = None
        self._tag = tag

    def __repr__(self) -> str:
        """Represent as string."""
        return _tagged_repr(self, self._point, self._tag)

    @property
    def point(self) -> IntPoint:
        """Position of the cell in the grid."""
        return self._point

    @property
    def tag(self) -> Optional[str]:
        """Tag used to look up the cell."""
        return self._tag

######################################################################

class DiagramRow:
    """A row in the diagram."""

    def __init__(
            self,
            index: int,
            tags: Iterable[Optional[str]],
    ):
        """Initialize the row."""
        self._index = index
        cells = []
        for j, tag in enumerate(tags):
            point = IntPoint(i=index, j=j)
            cell = DiagramCell(point, tag)
            cells.append(cell)
        self._cells = cells

    def __repr__(self) -> str:
        """Represent as string."""
        return class_str(self, self._index)

    def __len__(self) -> int:
        """Return the number of cells."""
        return len(self._cells)

    def __iter__(self) -> Iterator[DiagramCell]:
        """Iterate over the cells."""
        yield from self._cells

    def expand(self, count: int) -> None:
        """Add cells at the end if the row is shorter than the given length."""
        cells = self._cells
        current = len(cells)
        i = self._index
        for j in range(current, count):
            point = IntPoint(i=i, j=j)
            cell = DiagramCell(point)
            cells.append(cell)

######################################################################

class DiagramGrid:
    """Contains the cells of the diagram."""

    def __init__(self) -> None:
        """Initialize an empty grid."""
        self._rows: List[DiagramRow] = []

    def __repr__(self) -> str:
        """Represent as string."""
        content = grid_str(self.height, self.width)
        return class_str(self, content)

    def __iter__(self) -> Iterator[DiagramRow]:
        """Iterate over the rows."""
        yield from self._rows

    @property
    def height(self) -> int:
        """Number of rows."""
        return len(self._rows)

    @property
    def width(self) -> int:
        """Number of columns."""
        rows = self._rows
        if rows:
            return len(rows[0])
        return 0

    def add_row(self, tags: Iterable[Optional[str]]) -> None:
        """Add a row of cells to the grid."""
        index = len(self._rows)
        row = DiagramRow(index, tags)
        rows = self._rows
        rows.append(row)
        # Adjust the width of the rows.
        new_width = max(self.width, len(row))
        for row in rows:
            row.expand(new_width)

    def cells_containing(self, tags: Iterable[str]) -> Iterator[DiagramCell]:
        """Iterate over the cells that contain the given tags.

        It calculates the minimum rectangular area that contains all
        the cells with the given tags.  The iterator iterates over all
        the cells in the rectangular area (i.e. not only the cells
        with the given tags).  It yields the cells in the order that
        they are stored in the grid, i.e. the order of the tags is
        irrelevant.

        """
        points = []
        for cell in self._cells_tagged(tags):
            points.append(cell.point)
        bounds = IntBounds.containing(points)
        if bounds:
            yield from self._cells_covering(bounds)

    def _cells_tagged(self, tags: Iterable[str]) -> Iterator[DiagramCell]:
        """Iterate over the cells with the given tags.

        The iterator yields the cells in the order that they are
        stored in the grid.  The order of the tags is irrelevant.

        """
        tag_set = set(tags)
        for cell in self._cells():
            tag = cell.tag
            if tag and tag in tag_set:
                yield cell

    def _cells_covering(self, bounds: IntBounds) -> Iterator[DiagramCell]:
        """Iterate over the cells covering the bounding box.

        The iterator yields the cells in the order that they are
        stored in the grid.

        """
        for row in self:
            for cell in row:
                point = cell.point
                if (
                        point.i >= bounds.imin and point.i <= bounds.imax and
                        point.j >= bounds.jmin and point.j <= bounds.jmax
                ):
                    yield cell

    def _cells(self) -> Iterator[DiagramCell]:
        """Iterate over the cells.

        The iterator yields the cells in the order that they are
        stored in the grid.

        """
        for row in self:
            yield from row

######################################################################

class Node:
    """Endpoint of a connection on a block."""

    def __init__(self, cell: DiagramCell):
        """Initialize and place in the given cell."""
        self._cell = cell

    def __repr__(self) -> str:
        """Represent as string."""
        return _tagged_repr(self, self.point, self.tag)

    @property
    def point(self) -> IntPoint:
        """Position of the node in the diagram grid."""
        return self._cell.point

    @property
    def tag(self) -> Optional[str]:
        """Tag of the cell at the point."""
        return self._cell.tag

######################################################################

class Label:
    """Text on a diagram element."""

    def __init__(self, attrs: TextAttributes):
        """Initialize with the given attributes."""
        self._attributes = attrs

    @property
    def attributes(self) -> TextAttributes:
        """Attributes of the label."""
        return self._attributes

######################################################################

class Block:
    """Represents a block of the diagram."""

    def __init__(
            self,
            index: int, name: Optional[str] = None,
            **attrs: AttributeMap
    ):
        """Initialize the block (with optional attributes)."""
        self._index = index
        self._name = name
        self._attributes = self._make_attributes(**attrs)
        self._label = self._make_label()
        self._nodes: List[Node] = []
        self._bounds: Optional[IntBounds] = None

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def index(self) -> int:
        """Sequence number of the block in the diagram."""
        return self._index

    @property
    def name(self) -> Optional[str]:
        """Name of the block."""
        return self._name

    def description(self) -> str:
        """Return a description of the block."""
        content = str(self._index)
        name = self._name
        if name:
            content += f", name={repr(name)}"
        return content

    @property
    def attributes(self) -> BlockAttributes:
        """Attributes attached to the block."""
        return self._attributes

    @property
    def bounds(self) -> Optional[IntBounds]:
        """Bounding box of the block in the diagram grid."""
        bounds = self._bounds
        if bounds:
            return bounds.copy()
        return None

    @property
    def label(self) -> Optional[Label]:
        """Label to draw on the block."""
        return self._label

    def nodes(self) -> Iterator[Node]:
        """Iterate over the nodes."""
        yield from self._nodes

    def overlaps_with(self, other: 'Block') -> bool:
        """True if the two blocks have common nodes."""
        nodes_1 = set(self.nodes())
        nodes_2 = set(other.nodes())
        inter = nodes_1.intersection(nodes_2)
        return bool(inter)

    def add_node(self, node: Node) -> None:
        """Associate the block with the node.

        It preserves the order of the nodes and ensures that no node
        is added more than once.

        """
        nodes = self._nodes
        if node not in nodes:
            nodes.append(node)
        # Recalculate the bounding box.
        self._update_bounds()

    def _update_bounds(self) -> None:
        """Update the bounding box covered by the nodes."""
        points = []
        for node in self._nodes:
            points.append(node.point)
        self._bounds = IntBounds.containing(points)

    def _make_attributes(self, **attrs: AttributeMap) -> BlockAttributes:
        """Create the attributes held in the object."""
        attributes = Attributes(**attrs)
        # Use the name if the label is not defined.
        if 'label' not in attributes:
            attributes['label'] = self._name
        return BlockAttributes(**attributes)

    def _make_label(self) -> Optional[Label]:
        """Create the label of the block."""
        attrs = self._attributes
        if not attrs.label:
            return None
        return Label(attrs)

######################################################################

class SubBlock:
    """Part of a block that consists of specific nodes."""

    def __init__(self, block: Block, tag: Optional[str] = None):
        """Initialize for a given block and optional cell tag."""
        self._block = block
        self._tag = tag
        self._name = self._make_name()
        self._nodes = self._collect_nodes()

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._name)
        return class_str(self, content)

    def __bool__(self) -> bool:
        """Return true if the block is placed on the diagram grid."""
        return bool(self._nodes)

    @property
    def name(self) -> str:
        """Name of the sub-block."""
        return self._name

    @property
    def block(self) -> Block:
        """The block."""
        return self._block

    @property
    def tag(self) -> Optional[str]:
        """The tag used to subset the block."""
        return self._tag

    def outer_nodes(self) -> Iterator[Node]:
        """Iterate over the subset of nodes at the sides of the block."""
        bounds = self._block.bounds
        if bounds:
            for node in self._nodes:
                if bounds.on_perimeter(node.point):
                    yield node

    def _make_name(self) -> str:
        """Create a name for the object."""
        block_name = self._block.name
        tag = self._tag
        # It shouldn't be possible to have a connection end without a
        # name.
        assert block_name or tag
        strings = []
        if block_name:
            strings.append(block_name)
        if tag:
            strings.append(tag)
        return ":".join(strings)

    def _collect_nodes(self) -> List[Node]:
        """Return the nodes of the sub-block."""
        nodes: List[Node] = []
        tag = self._tag
        for node in self._block.nodes():
            if not tag or node.tag == tag:
                nodes.append(node)
        return nodes

######################################################################

class Connection:
    """A connection between two blocks in the diagram."""

    def __init__(
            self,
            index: int,
            start: SubBlock, end: SubBlock,
            group: Optional[str] = None,
            **attrs: AttributeMap
    ):
        """Initialize a connection between the given blocks."""
        self._index = index
        self._start = start
        self._end = end
        self._group = group
        self._attributes = ConnectionAttributes(**attrs)
        self._start_label: Optional[Label] = None
        self._middle_label: Optional[Label] = None
        self._end_label: Optional[Label] = None

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def index(self) -> int:
        """Index number of the connection in the diagram."""
        return self._index

    @property
    def start(self) -> SubBlock:
        """Source block of the connection."""
        return self._start

    @property
    def end(self) -> SubBlock:
        """Destination block of the connection."""
        return self._end

    @property
    def group(self) -> Optional[str]:
        """Group to which the connection belongs."""
        return self._group

    @property
    def attributes(self) -> ConnectionAttributes:
        """Attributes attached to the connection."""
        return self._attributes

    @property
    def start_label(self) -> Optional[Label]:
        """Label at the start of the connection."""
        return self._start_label

    @property
    def middle_label(self) -> Optional[Label]:
        """Label near the middle of the connection."""
        return self._middle_label

    @property
    def end_label(self) -> Optional[Label]:
        """Label at the end of the connection."""
        return self._end_label

    def label(self, position: ConnectionLabelPosition) -> Optional[Label]:
        """Return the label at the given position."""
        if position is ConnectionLabelPosition.START:
            return self._start_label
        if position is ConnectionLabelPosition.MIDDLE:
            return self._middle_label
        if position is ConnectionLabelPosition.END:
            return self._end_label
        return None

    def set_start_label(self, **attrs: AttributeMap) -> None:
        """Set the label at the start of the connection."""
        self._start_label = self._make_label(**attrs)

    def set_middle_label(self, **attrs: AttributeMap) -> None:
        """Set the label near the middle of the connection."""
        self._middle_label = self._make_label(**attrs)

    def set_end_label(self, **attrs: AttributeMap) -> None:
        """Set the label at the end of the connection."""
        self._end_label = self._make_label(**attrs)

    def _make_label(self, **attrs: AttributeMap) -> Label:
        """Create a label for the connection."""
        attributes = Attributes()
        attributes.merge(self._attributes.text_attributes_as_map())
        attributes.merge(attrs)
        text_attributes = LabelAttributes(**attributes)
        return Label(text_attributes)

    def description(self) -> str:
        """Return a description of the connection."""
        index = self._index
        ends = self.ends_description()
        return f"{index}, {ends}"

    def ends_description(self) -> str:
        """Return a description of the two ends of the connection."""
        start = self._start.name
        end = self._end.name
        ends = vector_repr(start, end)
        return f"ends={ends}"

######################################################################

class Diagram:
    """Container for the blocks and connections of the diagram."""

    def __init__(self, ddef: DiagramDef):
        """Initialize from the definition."""
        self._attributes = DiagramAttributes(**ddef.attributes)
        self._grid = self._make_grid(ddef)
        self._label = self._make_label()
        # The following will all be initialized simultaneously.
        self._blocks: List[Block] = []
        self._blocks_by_name: Dict[str, Block] = {}
        self._nodes: List[Node] = []
        self._nodes_to_blocks: Dict[Node, List[Block]] = {}
        self._points_to_nodes: Dict[IntPoint, Node] = {}
        self._init_blocks(ddef)
        # Done, now do the connections.
        self._connections = self._make_connections(ddef)

    @property
    def attributes(self) -> DiagramAttributes:
        """Attributes attached to the diagram."""
        return self._attributes

    @property
    def label(self) -> Optional[Label]:
        """Label to draw as a title for the diagram."""
        return self._label

    def blocks(self) -> Iterator[Block]:
        """Iterate over the blocks.

        The iterator yields the blocks in the order they were added to
        the diagram.

        """
        yield from self._blocks

    def nodes(self) -> Iterator[Node]:
        """Iterate over the nodes of all the blocks."""
        yield from self._nodes

    def node_blocks(self, node: Node) -> Iterator[Block]:
        """Iterate over the blocks connected to a node."""
        yield from self._nodes_to_blocks[node]

    def connections(self) -> Iterator[Connection]:
        """Iterate over the connections."""
        yield from self._connections

    @property
    def grid(self) -> DiagramGrid:
        """The grid that contains the blocks."""
        return self._grid

    @staticmethod
    def _make_grid(ddef: DiagramDef) -> DiagramGrid:
        """Create the grid from the diagram definition."""
        grid = DiagramGrid()
        for row_def in ddef.row_defs():
            grid.add_row(row_def)
        return grid

    def _make_label(self) -> Optional[Label]:
        """Create the label of the diagram."""
        attrs = self._attributes
        if not attrs.label:
            return None
        return Label(attrs)

    def _init_blocks(self, ddef: DiagramDef) -> None:
        """Create the blocks from the definition."""
        self._blocks.clear()
        self._nodes.clear()
        self._nodes_to_blocks.clear()
        self._points_to_nodes.clear()
        bdefs = self._block_defs(ddef)
        self._make_blocks(bdefs)

    @staticmethod
    def _block_defs(ddef: DiagramDef) -> Iterator[BlockDef]:
        """Block definitions to turn into blocks."""
        yield from ddef.block_defs()
        yield from ddef.auto_block_defs()

    def _make_blocks(self, bdefs: Iterable[BlockDef]) -> None:
        """Use the block definitions to create blocks."""
        blocks = self._blocks
        by_name = self._blocks_by_name
        nodes = self._nodes
        nodes_to_blocks = self._nodes_to_blocks
        points_to_nodes = self._points_to_nodes
        grid = self._grid
        for index, bdef in enumerate(bdefs):
            name = bdef.name
            block = Block(index, name, **bdef.attributes)
            blocks.append(block)
            tags = set()
            if name:
                by_name[name] = block
                # The name of the block is a tag itself!
                tags.add(name)
            tags.update(bdef.tags)
            # Find or create the nodes.
            for cell in grid.cells_containing(tags):
                point = cell.point
                node = points_to_nodes.get(point)
                if not node:
                    node = Node(cell)
                    nodes.append(node)
                    points_to_nodes[point] = node
                block.add_node(node)
                if node not in nodes_to_blocks:
                    nodes_to_blocks[node] = []
                nodes_to_blocks[node].append(block)

    def _make_connections(self, ddef: DiagramDef) -> List[Connection]:
        """Create the connections from the definition."""
        connections: List[Connection] = []
        for cdef in ddef.connection_defs():
            index = len(connections)
            connection = self._make_connection(index, cdef)
            if connection:
                connections.append(connection)
        return connections

    def _make_connection(
            self, index: int, cdef: ConnectionDef
    ) -> Optional[Connection]:
        """Create a connection from a connection definition."""
        start = self._sub_block(cdef.start)
        end = self._sub_block(cdef.end)
        if not (start and end):
            return None
        # Cannot create connection between overlapping blocks.
        block1 = start.block
        block2 = end.block
        if block1.overlaps_with(block2):
            tmpl = "Blocks '{}' and '{}' overlap, connection rejected"
            log_warning(tmpl.format(block1.name, block2.name))
            return None
        # Everything seems OK, let's make the connection.
        connection = Connection(
            index, start, end, cdef.group, **cdef.attributes)
        # Add the labels.
        if cdef.start_label:
            connection.set_start_label(**cdef.start_label.attributes)
        if cdef.middle_label:
            connection.set_middle_label(**cdef.middle_label.attributes)
        if cdef.end_label:
            connection.set_end_label(**cdef.end_label.attributes)
        return connection

    def _sub_block(self, ndef: SubBlockDef) -> Optional[SubBlock]:
        """Retrieve the subset of the block from the definition."""
        if isinstance(ndef, str):
            block_name = ndef
            tag = None
        else:
            block_name, tag = ndef
        block = self._block(block_name)
        if block:
            sub = SubBlock(block, tag)
            if sub:
                return sub
            log_warning(f"Node '{block_name}' is not placed")
            return None
        return None

    def _block(self, name: str) -> Optional[Block]:
        """Retrieve a block by name."""
        block = self._blocks_by_name.get(name)
        if not block:
            log_warning(f"Block '{name}' does not exist")
        return block

    def _pretty_print(self) -> None:
        """Print the diagram for debugging purposes."""
        ind1 = indent(1)
        ind2 = indent(2)
        print("Blocks:")
        for block in self._blocks:
            print(f"{ind1}{block}")
        print("Connections:")
        for connection in self._connections:
            print(f"{ind1}{connection}")
        print("Rows:")
        for row in self._grid:
            print(f"{ind1}{row}:")
            for cell in row:
                print(f"{ind2}{cell}")

######################################################################

def _tagged_repr(obj: object, point: IntPoint, tag: Optional[str]) -> str:
    """Helper for the representation methods of tagged point objects."""
    i = point.i
    j = point.j
    content = f"i={i}, j={j}"
    if tag:
        content += f", tag={repr(tag)}"
    return class_str(obj, content)
