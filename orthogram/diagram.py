"""Provides the elements of a diagram."""

from enum import Enum, auto

from typing import (
    cast,
    Any,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from .geometry import IntPoint, Orientation
from .util import log_warning

######################################################################

# Abstract mapping from attribute names to attribute values.
AttributeMap = Mapping[str, Any]

# Concrete mapping from attribute names to attribute values.
AttributeDict = Dict[str, Any]

######################################################################

class LabelPosition(Enum):
    """Position of the label of an element relative to its shape."""
    BOTTOM = auto()
    TOP = auto()

######################################################################

class LineAttributes:
    """Collection of attributes relevant to linear objects."""

    def __init__(self) -> None:
        """Initialize the attributes with default values."""
        self._stroke: Optional[str] = "black"
        self._stroke_dasharray: Optional[str] = None
        self._stroke_width = 2.0

    def _set_line_attributes(self, attrs: AttributeMap) -> None:
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

    def _set_area_attributes(self, attrs: AttributeMap) -> None:
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
        """Minimum height of the shape."""
        return self._min_height

    @property
    def min_width(self) -> float:
        """Minimum width of the shape."""
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
        self._text_orientation = Orientation.HORIZONTAL

    def _set_text_attributes(self, attrs: AttributeMap) -> None:
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
        if 'text_orientation' in attrs:
            self._text_orientation = cast(
                Orientation, attrs['text_orientation'])

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

    @property
    def text_orientation(self) -> Orientation:
        """Orientation of the text."""
        return self._text_orientation

######################################################################

class Pin:
    """Diagram position occupied by a terminal."""

    def __init__(self, name: str, point: IntPoint):
        """Initialize with the given name and position."""
        self._name = name
        self._point = point

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({})".format(self.__class__.__name__, self._name)

    @property
    def name(self) -> str:
        """Name that identifies the pin."""
        return self._name

    @property
    def point(self) -> IntPoint:
        """Position of the pin in the diagram."""
        return self._point

######################################################################

class TerminalAttributes(LineAttributes, AreaAttributes, TextAttributes):
    """Collection of attributes relevant to link terminals."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the attributes with the given values."""
        LineAttributes.__init__(self)
        AreaAttributes.__init__(self)
        TextAttributes.__init__(self)
        self._min_height = 48.0
        self._min_width = 96.0
        self.set_attributes(**attrs)

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        self._set_line_attributes(attrs)
        self._set_area_attributes(attrs)
        self._set_text_attributes(attrs)
        self._set_terminal_attributes(attrs)

    def _set_terminal_attributes(self, attrs: AttributeMap) -> None:
        """Set the attributes of the terminal to the given values."""
        pass

######################################################################

class Terminal:
    """Links terminate here."""

    def __init__(self, name: str, **attrs: AttributeMap):
        """Initialize the terminal (with optional attributes)."""
        self._name = name
        self._attributes = TerminalAttributes(**attrs)
        self._pins: List[Pin] = []

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({};pins={})".format(
            self.__class__.__name__,
            self._name,
            len(self._pins),
        )

    @property
    def name(self) -> str:
        """A name that identifies the terminal."""
        return self._name

    @property
    def attributes(self) -> TerminalAttributes:
        """Attributes attached to the terminal."""
        return self._attributes

    def can_occupy(self, p: IntPoint, length: int) -> bool:
        """Answer whether the terminal can occupy a range of positions.

        It prints an appropriate warning when the result is negative.

        """
        pins = self._pins
        # A terminal without pins can be always expanded.
        if not pins:
            return True
        above = False
        overlap = False
        jmin = jmax = -1
        for pin in self._pins:
            pp = pin.point
            if pp == p:
                # This shouldn't happen actually.
                overlap = True
            if pp.i == p.i - 1:
                # There is a chunk directly above, good.
                above = True
            if jmin < 0 or pp.j < jmin:
                jmin = pp.j
            if jmax < 0 or pp.j > jmax:
                jmax = pp.j
        if overlap:
            t = "Pins of terminal '{}' overlap"
            log_warning(t.format(self._name))
            return False
        if not above:
            t = "Gap detected between pins of terminal '{}'"
            log_warning(t.format(self._name))
            return False
        if jmin != p.j:
            t = "Pins of terminal '{}' are not vertically aligned"
            log_warning(t.format(self._name))
            return False
        width = jmax - jmin + 1
        if width != length:
            t = "Pin range for terminal '{}' has wrong length"
            log_warning(t.format(self._name))
            return False
        return True

    def occupy(self, p: IntPoint) -> Pin:
        """Occupy the given position in the diagram.

        It returns the terminal pin created for the position.

        """
        pins = self._pins
        pin_name = "{}.{}".format(self._name, len(pins))
        pin = Pin(pin_name, p)
        pins.append(pin)
        return pin

    def pins(self) -> Iterator[Pin]:
        """Return an iterator over the pins of the terminal."""
        yield from self._pins

    def is_placed(self) -> bool:
        """Return true if the terminal occupies positions in the diagram."""
        return len(self._pins) > 0

    def label(self) -> str:
        """Return a label to draw on the terminal in the diagram."""
        label = self._attributes.label
        # Compare against None - the empty string is a valid label.
        if label is None:
            return self._name
        else:
            return label

######################################################################

class Cell:
    """Position in a grid, may hold a terminal pin."""

    def __init__(
            self,
            terminal: Optional[Terminal] = None,
            pin: Optional[Pin] = None,
    ):
        """Initialize with the given contents."""
        self._terminal = terminal
        self._pin = pin

    @property
    def terminal(self) -> Optional[Terminal]:
        """The terminal that has a pin in this cell."""
        return self._terminal

    @property
    def pin(self) -> Optional[Pin]:
        """Terminal pin in this cell."""
        return self._pin

######################################################################

class DiagramRow:
    """A row or column in the diagram."""

    def __init__(self, cells: Sequence[Cell]):
        """Initialize the row with terminal pins and empty spaces."""
        self._cells: List[Cell] = []
        if cells:
            self._cells.extend(cells)

    def __len__(self) -> int:
        """Get the number of pins and empty spaces in the row."""
        return len(self._cells)

    def __getitem__(self, j: int) -> Cell:
        """Get the cell which is at the given position."""
        return self._cells[j]

    def __iter__(self) -> Iterator[Cell]:
        """Get an iterator over the cells."""
        yield from self._cells

######################################################################

class LinkAttributes(LineAttributes):
    """Collection of attributes relevant to links."""

    def __init__(self, **attrs: AttributeMap):
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

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        self._set_line_attributes(attrs)
        self._set_link_attributes(attrs)

    def _set_link_attributes(self, attrs: AttributeMap) -> None:
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
    """A link between two terminals in the diagram."""

    def __init__(self, start: Terminal, end: Terminal, **attrs: AttributeMap):
        """Initialize a link between the given terminals."""
        self._start = start
        self._end = end
        self._attributes = LinkAttributes(**attrs)

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({}->{})".format(
            self.__class__.__name__,
            self._start.name,
            self._end.name,
        )

    @property
    def start(self) -> Terminal:
        """Source terminal of the link."""
        return self._start

    @property
    def end(self) -> Terminal:
        """Destination terminal of the link."""
        return self._end

    @property
    def attributes(self) -> LinkAttributes:
        """Attributes attached to the link."""
        return self._attributes

######################################################################

class DiagramAttributes(LineAttributes, AreaAttributes, TextAttributes):
    """Collection of attributes relevant to diagrams."""

    def __init__(self, **attrs: AttributeMap):
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
        self._padding = 0.0
        self._row_margin = 24.0
        self._stretch = True
        self._stroke_width = 0.0
        self.set_attributes(**attrs)

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        self._set_line_attributes(attrs)
        self._set_area_attributes(attrs)
        self._set_text_attributes(attrs)
        self._set_diagram_attributes(attrs)

    def _set_diagram_attributes(self, attrs: AttributeMap) -> None:
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
    def label_distance(self) -> float:
        """Distance of the label from the border."""
        return self._label_distance

    @property
    def label_position(self) -> LabelPosition:
        """Position of the label."""
        return self._label_position

    @property
    def link_distance(self) -> float:
        """Distance between links."""
        return self._link_distance

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
    """Container for the terminals and links of the diagram."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the diagram with the given attributes."""
        self._terminals: Dict[str, Terminal] = {}
        self._pins_to_terminals: Dict[Pin, Terminal] = {}
        self._rows: List[DiagramRow] = []
        self._links: List[Link] = []
        self._attributes = DiagramAttributes(**attrs)

    @property
    def attributes(self) -> DiagramAttributes:
        """Attributes attached to the diagram."""
        return self._attributes

    def add_terminal(self, name: str, **attrs: AttributeMap) -> None:
        """Add a new terminal to the diagram.

        Rejects the terminal with a warning if there is already a
        terminal registered with the same name.

        See TerminalAttributes for a list of available attributes.

        """
        terminals = self._terminals
        if name in terminals:
            log_warning("Terminal '{}' already exists".format(name))
            return
        terminal = Terminal(name, **attrs)
        terminals[name] = terminal

    def _terminal(self, name: str) -> Optional[Terminal]:
        """Retrieve a terminal by name.

        If a terminal with the given name does not exist, it prints a
        warning and returns None.

        """
        terminal = self._terminals.get(name)
        if not terminal:
            log_warning("Terminal '{}' does not exist".format(name))
        return terminal

    def add_row(self, terminal_names: Sequence[Optional[str]]) -> None:
        """Add a row at the end of the diagram.

        The input is a sequence of names that will be used to look up
        the terminals whose pins are to be placed in the row.  If a
        name does not correspond to a terminal, the method prints a
        warning and leaves an empty space in the row.  Use an empty
        string or None to add an empty space on purpose.

        You can place the same terminal in more than one positions to
        occupy a rectangle in the diagram grid.  The method will check
        the geometry of the expanded terminal and will reject
        positions that cause non-rectangular terminals.

        """
        pts = self._pins_to_terminals
        rows = self._rows
        i = len(rows)
        j = 0
        cells: List[Cell] = []
        for name, length in self._split_row(terminal_names):
            terminal: Optional[Terminal] = None
            if name:
                terminal = self._terminal(name)
                if terminal:
                    p = IntPoint(i, j)
                    if not terminal.can_occupy(p, length):
                        terminal = None
            for _ in range(length):
                if terminal:
                    p = IntPoint(i, j)
                    pin = terminal.occupy(p)
                    cell = Cell(terminal, pin)
                    cells.append(cell)
                    pts[pin] = terminal
                else:
                    cells.append(Cell())
                j += 1
        row = DiagramRow(cells)
        rows.append(row)

    def _split_row(
            self, names: Sequence[Optional[str]]
    ) -> Iterator[Tuple[Optional[str], int]]:
        """Break the row definition into chunks of the same name.

        This method returns an iterator that generates (name, length)
        pairs.

        """
        chunk: List[Optional[str]] = []
        for name in names:
            if not chunk or name == chunk[-1]:
                chunk.append(name)
            else:
                yield chunk[0], len(chunk)
                chunk = [name]
        if chunk:
            yield chunk[0], len(chunk)

    def rows(self) -> Iterator[DiagramRow]:
        """Return an iterator over the rows."""
        yield from self._rows

    def n_rows(self) -> int:
        """Return the number of rows in the diagram."""
        return len(self._rows)

    def max_row(self) -> int:
        """Return the length of the longest row.

        It takes into account both occupied and empty positions.

        """
        result = 0
        for row in self._rows:
            result = max(result, len(row))
        return result

    def pin_terminal(self, pin: Pin) -> Terminal:
        """Return the terminal that owns the given pin."""
        return self._pins_to_terminals[pin]

    def add_link(
            self,
            start_terminal_name: str,
            end_terminal_name: str,
            **attrs: AttributeMap,
    ) -> None:
        """Create a link between two terminals.

        The process fails with a warning if:

        1. any of the two terminal names does not correspond to a
           terminal registered in the diagram or

        2. any of the two terminals has not a pin in a row or

        3. start and end are both the same terminal.

        See DiagramAttributes for a list of available attributes.

        """
        # Self connections are not supported.
        if start_terminal_name == end_terminal_name:
            log_warning("Cannot connect '{}' to itself".
                        format(start_terminal_name))
            return
        # Ensure that the two terminals have been registered and
        # placed.
        start = self._terminal(start_terminal_name)
        end = self._terminal(end_terminal_name)
        if not (start and end):
            return
        ok = True
        for terminal in (start, end):
            if not terminal.is_placed():
                log_warning("Terminal '{}' is not placed".format(terminal.name))
                ok = False
        if not ok:
            return
        # We have both terminals, let's make the connection.
        link = Link(start, end, **attrs)
        self._links.append(link)

    def add_links(
            self,
            start_terminal_names: Sequence[str],
            end_terminal_names: Sequence[str],
            **attrs: AttributeMap,
    ) -> None:
        """Create many links at once.

        If the number of start terminals is n and the number of end
        terminals in m, then the number of links created will be n*m
        (assuming all terminals exist and are placed.)  See add_link()
        for further information.

        """
        for start in start_terminal_names:
            for end in end_terminal_names:
                self.add_link(start, end, **attrs)

    def links(self) -> Iterator[Link]:
        """Return the links of the diagram."""
        yield from self._links

    def _pretty_print(self) -> None:
        """Print the diagram for debugging purposes."""
        print("Terminals:")
        for terminal in self._terminals.values():
            print("\t{}".format(terminal))
        print("Rows:")
        for i, row in enumerate(self._rows):
            print("\tRow {}:".format(i))
            for row_terminal in row:
                print("\t\t{}".format(row_terminal))
        print("Links:")
        for link in self._links:
            print("\t{} -> {}".format(link.start, link.end))
