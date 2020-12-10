"""Provides the elements of a diagram."""

from enum import Enum, auto

from typing import (
    cast,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
)

from .geometry import Orientation
from .util import log_warning

######################################################################

class LabelPosition(Enum):
    """Position of the label of an element relative to its shape."""
    BOTTOM = auto()
    TOP = auto()

######################################################################

# Attributes as key-value pairs.
Attributes = Dict[str, Any]

######################################################################

class LineAttributes:
    """Collection of attributes relevant to linear objects."""

    def __init__(self) -> None:
        """Initialize the attributes with default values."""
        self._stroke: Optional[str] = "black"
        self._stroke_dasharray: Optional[str] = None
        self._stroke_width = 2.0

    def _set_line_attributes(self, attrs: Attributes) -> None:
        """Set the line attributes to the given values."""
        if 'stroke' in attrs:
            self._stroke = cast(Optional[str], attrs['stroke'])
        if 'stroke_dasharray' in attrs:
            self._stroke_dasharray = cast(Optional[str],
                                          attrs['stroke_dasharray'])
        if 'stroke_width' in attrs:
            self._stroke_width = cast(float, attrs['stroke_width'])

    @property
    def stroke(self) -> Optional[str]:
        """Color of the line (e.g. "black".)"""
        return self._stroke

    @property
    def stroke_dasharray(self) -> Optional[str]:
        """Dash pattern of the line (e.g. "4 4".)"""
        return self._stroke_dasharray

    @property
    def stroke_width(self) -> float:
        """Width of the line (in pt.)"""
        return self._stroke_width

######################################################################

class AreaAttributes:
    """Collection of attributes relevant to 2D shapes."""

    def __init__(self) -> None:
        """Initialize the attributes with default values."""
        self._fill: Optional[str] = "none"
        self._min_height = 0.0
        self._min_width = 0.0

    def _set_area_attributes(self, attrs: Attributes) -> None:
        """Set the area attributes to the given values."""
        if 'fill' in attrs:
            self._fill = cast(Optional[str], attrs['fill'])
        if 'min_height' in attrs:
            self._min_height = cast(float, attrs['min_height'])
        if 'min_width' in attrs:
            self._min_width = cast(float, attrs['min_width'])

    @property
    def fill(self) -> Optional[str]:
        """Color of the interior (e.g. "white".)"""
        return self._fill

    @property
    def min_height(self) -> float:
        """Minimum height of the node."""
        return self._min_height

    @property
    def min_width(self) -> float:
        """Minimum width of the node."""
        return self._min_width

######################################################################

class TextAttributes:
    """Collection of attributes relevant to text."""

    def __init__(self) -> None:
        """Initialize the attributes with the given values."""
        self._font_family: Optional[str] = None
        self._font_size = 10.0
        self._font_style: Optional[str] = None
        self._font_weight: Optional[str] = None
        self._label: Optional[str] = None
        self._text_fill: Optional[str] = "black"
        self._text_line_height = 1.25

    def _set_text_attributes(self, attrs: Attributes) -> None:
        """Set the text attributes to the given values."""
        if 'font_family' in attrs:
            self._font_family = cast(Optional[str], attrs['font_family'])
        if 'font_size' in attrs:
            self._font_size = cast(float, attrs['font_size'])
        if 'font_style' in attrs:
            self._font_style = cast(Optional[str], attrs['font_style'])
        if 'font_weight' in attrs:
            self._font_weight = cast(Optional[str], attrs['font_weight'])
        if 'label' in attrs:
            self._label = cast(Optional[str], attrs['label'])
        if 'text_fill' in attrs:
            self._text_fill = cast(Optional[str], attrs['text_fill'])
        if 'text_line_height' in attrs:
            self._text_line_height = cast(float, attrs['text_line_height'])

    @property
    def font_family(self) -> Optional[str]:
        """Font family of text (e.g. "sans".)"""
        return self._font_family

    @property
    def font_size(self) -> float:
        """Font size of text (in pt.)"""
        return self._font_size

    @property
    def font_style(self) -> Optional[str]:
        """Font style of text (e.g. "italic".)"""
        return self._font_style

    @property
    def font_weight(self) -> Optional[str]:
        """Font weight of text (e.g. "bold".)"""
        return self._font_weight

    @property
    def label(self) -> Optional[str]:
        """Text to draw on the element."""
        return self._label

    @property
    def text_fill(self) -> Optional[str]:
        """Color of text (e.g. "black".)"""
        return self._text_fill

    @property
    def text_line_height(self) -> float:
        """Height of text line (in em.)"""
        return self._text_line_height

######################################################################

class NodeAttributes(LineAttributes, AreaAttributes, TextAttributes):
    """Collection of attributes relevant to nodes."""

    def __init__(self, **attrs: Attributes):
        """Initialize the attributes with the given values."""
        LineAttributes.__init__(self)
        AreaAttributes.__init__(self)
        TextAttributes.__init__(self)
        self._min_height = 48.0
        self._min_width = 96.0
        self.set_attributes(**attrs)

    def set_attributes(self, **attrs: Attributes) -> None:
        """Set the attributes to the given values."""
        self._set_line_attributes(attrs)
        self._set_area_attributes(attrs)
        self._set_text_attributes(attrs)
        self._set_node_attributes(attrs)

    def _set_node_attributes(self, attrs: Attributes) -> None:
        """Set the node attributes to the given values."""
        pass

######################################################################

class Node:
    """A node in a diagram."""

    def __init__(self, name: str, **attrs: Attributes):
        """Initialize the node (with optional attributes)."""
        self._name = name
        self._attributes = NodeAttributes(**attrs)

    @property
    def name(self) -> str:
        """A name that identifies the node."""
        return self._name

    @property
    def attributes(self) -> NodeAttributes:
        """Attributes attached to the node."""
        return self._attributes

    def label(self) -> str:
        """Return a label to draw over the node in the diagram."""
        label = self._attributes.label
        # Compare against None - the empty string is a valid label.
        if label is None:
            return self._name
        else:
            return label

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({})".format(self.__class__.__name__, self._name)

######################################################################

# Node or empty space in a row.
_RowElement = Optional[Node]

######################################################################

class DiagramRow:
    """A row or column in the diagram."""

    def __init__(self, elements: Sequence[_RowElement]):
        """Initialize the row with nodes and empty spaces."""
        self._elements: List[_RowElement] = []
        if elements:
            self._elements.extend(elements)

    def __len__(self) -> int:
        """Get the number of nodes and empty spaces in the row."""
        return len(self._elements)

    def __getitem__(self, j: int) -> Optional[Node]:
        """Get the element which is at the given position."""
        return self._elements[j]

    def __iter__(self) -> Iterator[Optional[Node]]:
        """Get an iterator over the nodes and empty spaces."""
        yield from self._elements

######################################################################

class LinkAttributes(LineAttributes):
    """Collection of attributes relevant to links."""

    def __init__(self, **attrs: Attributes):
        """Initialize the attributes with the given values."""
        LineAttributes.__init__(self)
        self._arrow_aspect = 1.5
        self._arrow_back = False
        self._arrow_base = 3.0
        self._arrow_forward = True
        self._buffer_fill: Optional[str] = None
        self._buffer_width: Optional[float] = None
        self._drawing_priority = 0
        self._end_bias: Optional[Orientation] = None
        self._group: Optional[str] = None
        self._start_bias: Optional[Orientation] = None
        self._stroke = "black"
        self.set_attributes(**attrs)

    def set_attributes(self, **attrs: Attributes) -> None:
        """Set the attributes to the given values."""
        self._set_line_attributes(attrs)
        self._set_link_attributes(attrs)

    def _set_link_attributes(self, attrs: Attributes) -> None:
        """Set the link attributes to the given values."""
        if 'arrow_aspect' in attrs:
            self._arrow_aspect = cast(float, attrs['arrow_aspect'])
        if 'arrow_back' in attrs:
            self._arrow_back = cast(bool, attrs['arrow_back'])
        if 'arrow_base' in attrs:
            self._arrow_base = cast(float, attrs['arrow_base'])
        if 'arrow_forward' in attrs:
            self._arrow_forward = cast(bool, attrs['arrow_forward'])
        if 'buffer_fill' in attrs:
            self._buffer_fill = cast(Optional[str], attrs['buffer_fill'])
        if 'buffer_width' in attrs:
            self._buffer_width = cast(Optional[float], attrs['buffer_width'])
        if 'drawing_priority' in attrs:
            self._drawing_priority = cast(int, attrs['drawing_priority'])
        if 'end_bias' in attrs:
            self._end_bias = cast(Optional[Orientation], attrs['end_bias'])
        if 'group' in attrs:
            self._group = cast(Optional[str], attrs['group'])
        if 'start_bias' in attrs:
            self._start_bias = cast(Optional[Orientation], attrs['start_bias'])

    @property
    def arrow_aspect(self) -> float:
        """Arrow aspect, length/width."""
        return self._arrow_aspect

    @property
    def arrow_back(self) -> bool:
        """Draw an arrow at the start of the link?"""
        return self._arrow_back

    @property
    def arrow_base(self) -> float:
        """Multiply stroke width with this to get arrow base width."""
        return self._arrow_base

    @property
    def arrow_forward(self) -> bool:
        """Draw an arrow at the end of the link?"""
        return self._arrow_forward

    @property
    def buffer_fill(self) -> Optional[str]:
        """Color of the buffer around the link."""
        return self._buffer_fill

    @property
    def buffer_width(self) -> Optional[float]:
        """Width of the buffer around the link."""
        return self._buffer_width

    @property
    def drawing_priority(self) -> int:
        """Relative priority when drawing links."""
        return self._drawing_priority

    @property
    def group(self) -> Optional[str]:
        """Group to which the link belongs."""
        return self._group

    @property
    def end_bias(self) -> Optional[Orientation]:
        """Orientation bias of the last segment."""
        return self._end_bias

    @property
    def start_bias(self) -> Optional[Orientation]:
        """Orientation bias of the first segment."""
        return self._start_bias

######################################################################

class Link:
    """A link between two nodes in the diagram."""

    def __init__(self, start: Node, end: Node, **attrs: Attributes):
        """Initialize the link between the given nodes."""
        self._start = start
        self._end = end
        self._attributes = LinkAttributes(**attrs)

    @property
    def start(self) -> Node:
        """First node of the link."""
        return self._start

    @property
    def end(self) -> Node:
        """Second and last node of the link."""
        return self._end

    @property
    def attributes(self) -> LinkAttributes:
        """Attributes attached to the link."""
        return self._attributes

######################################################################

class DiagramAttributes(LineAttributes, AreaAttributes, TextAttributes):
    """Collection of attributes relevant to diagrams."""

    def __init__(self, **attrs: Attributes):
        """Initialize the attributes with the given values."""
        LineAttributes.__init__(self)
        AreaAttributes.__init__(self)
        TextAttributes.__init__(self)
        self._collapse_links = False
        self._column_margin = 24.0
        self._font_size = 14.0
        self._label_distance = 6.0
        self._label_position = LabelPosition.TOP
        self._link_distance = 4.0
        self._min_height = 300.0
        self._min_width = 300.0
        self._padding = 24.0
        self._row_margin = 24.0
        self._stretch = True
        self._stroke_width = 0.0
        self.set_attributes(**attrs)

    def set_attributes(self, **attrs: Attributes) -> None:
        """Set the attributes to the given values."""
        self._set_line_attributes(attrs)
        self._set_area_attributes(attrs)
        self._set_text_attributes(attrs)
        self._set_diagram_attributes(attrs)

    def _set_diagram_attributes(self, attrs: Attributes) -> None:
        """Set the diagram attributes to the given values."""
        if 'collapse_links' in attrs:
            self._collapse_links = cast(bool, attrs['collapse_links'])
        if 'column_margin' in attrs:
            self._column_margin = cast(float, attrs['column_margin'])
        if 'label_distance' in attrs:
            self._label_distance = cast(float, attrs['label_distance'])
        if 'label_position' in attrs:
            self._label_position = cast(LabelPosition, attrs['label_position'])
        if 'link_distance' in attrs:
            self._link_distance = cast(float, attrs['link_distance'])
        if 'padding' in attrs:
            self._padding = cast(float, attrs['padding'])
        if 'row_margin' in attrs:
            self._row_margin = cast(float, attrs['row_margin'])
        if 'stretch' in attrs:
            self._stretch = cast(bool, attrs['stretch'])

    @property
    def collapse_links(self) -> bool:
        """Let links that belong to the same group overlap?."""
        return self._collapse_links

    @property
    def column_margin(self) -> float:
        """Margin between adjacent columns."""
        return self._column_margin

    @property
    def link_distance(self) -> float:
        """Distance between links."""
        return self._link_distance

    @property
    def label_distance(self) -> float:
        """Distance of the label from the border."""
        return self._label_distance

    @property
    def label_position(self) -> LabelPosition:
        """Position of the label."""
        return self._label_position

    @property
    def padding(self) -> float:
        """Distance between the objects inside the diagram and its border."""
        return self._padding

    @property
    def row_margin(self) -> float:
        """Margin between adjacent rows."""
        return self._row_margin

    @property
    def stretch(self) -> bool:
        """Stretch diagram to fill container?"""
        return self._stretch

######################################################################

class Diagram:
    """Container for the nodes and links of the diagram."""

    def __init__(self, **attrs: Attributes):
        """Initialize the diagram with the given attributes."""
        self._nodes: Dict[str, Node] = {}
        self._placed_nodes: Dict[Node, bool] = {}
        self._rows: List[DiagramRow] = []
        self._links: List[Link] = []
        self._attributes = DiagramAttributes(**attrs)

    @property
    def attributes(self) -> DiagramAttributes:
        """Attributes attached to the diagram."""
        return self._attributes

    def add_node(self, name: str, **attrs: Attributes) -> None:
        """Add a new node to the diagram.

        Rejects the node with a warning if there is already a node
        registered with the same name.

        See NodeAttributes for a list of available attributes.

        """
        nodes = self._nodes
        if name in nodes:
            log_warning("Node '{}' already exists".format(name))
            return
        node = Node(name, **attrs)
        nodes[name] = node

    def _node(self, name: str) -> Optional[Node]:
        """Retrieve a node by name.

        If a node with the given name does not exist, it prints a
        warning and returns None.

        """
        node = self._nodes.get(name)
        if not node:
            log_warning("Node '{}' does not exist".format(name))
        return node

    def add_row(self, node_names: Sequence[Optional[str]]) -> None:
        """Add a row at the end of the diagram.

        The input is a sequence of names that will be used to look up
        the nodes that are to be placed in the row.  If a name does
        not correspond to a node, the method prints a warning and
        leaves an empty space in the row.  Use an empty string or None
        to add an empty space on purpose.

        """
        elements = []
        placed = self._placed_nodes
        for name in node_names:
            node: Optional[Node] = None
            if name:
                node = self._node(name)
                if not node:
                    pass
                elif node in placed:
                    # Do not add the node to another row.
                    log_warning("Node '{}' is already placed".format(name))
                    node = None
                else:
                    # Mark node as placed, since we are going to add
                    # it below.
                    placed[node] = True
            # None is acceptable here, denoting an empty space.  Nodes
            # missing due to error will show up as empty spaces too.
            elements.append(node)
        row = DiagramRow(elements)
        self._rows.append(row)

    def rows(self) -> Iterator[DiagramRow]:
        """Return an iterator over the rows."""
        yield from self._rows

    def n_rows(self) -> int:
        """Return the number of rows in the diagram."""
        return len(self._rows)

    def max_row(self) -> int:
        """Return the length of the longest row.

        It takes into account both nodes and empty spaces.

        """
        result = 0
        for row in self._rows:
            result = max(result, len(row))
        return result

    def add_link(
            self,
            start_node_name: str,
            end_node_name: str,
            **attrs: Attributes,
    ) -> None:
        """Create a link between two nodes.

        The process fails with a warning if:

        1. any of the two node names does not correspond to a node
           registered in the diagram or

        2. any of the two nodes has not been placed in a row.

        See DiagramAttributes for a list of available attributes.

        """
        start = self._node(start_node_name)
        end = self._node(end_node_name)
        # Ensure that the two nodes were found and have been placed.
        if not (start and end):
            return
        placed = self._placed_nodes
        ok = True
        for node in (start, end):
            if node not in placed:
                log_warning("Node '{}' is not placed".format(node.name))
                ok = False
        if not ok:
            return
        # We have both nodes, let's make the connection.
        link = Link(start, end, **attrs)
        self._links.append(link)

    def add_links(
            self,
            start_node_names: Sequence[str],
            end_node_names: Sequence[str],
            **attrs: Attributes,
    ) -> None:
        """Create many links at once.

        If the number of start nodes is n and the number of end nodes
        in m, then the number of links created will be n*m (assuming
        all nodes exist and are placed.)  See add_link() for further
        information.

        """
        for start in start_node_names:
            for end in end_node_names:
                self.add_link(start, end, **attrs)

    def links(self) -> Iterator[Link]:
        """Return the links of the diagram."""
        yield from self._links

    def _pretty_print(self) -> None:
        """Print the diagram for debugging purposes."""
        print("Nodes:")
        for name, node in self._nodes.items():
            print("\t{}: {}".format(name, node))
        print("Rows:")
        for i, row in enumerate(self._rows):
            print("\tRow {}:".format(i))
            for row_node in row:
                print("\t\t{}".format(row_node))
        print("Links:")
        for link in self._links:
            print("\t{} -> {}".format(link.start, link.end))
