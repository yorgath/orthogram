"""Provides means to collect and merge attributes."""

from enum import Enum, auto

from typing import (
    cast,
    Any,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Set,
)

from .geometry import Orientation

######################################################################

# Attributes are key-value pairs, where the key is a string.
AttributeMap = Mapping[str, Any]

######################################################################

class Side(Enum):
    """Block sides."""

    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()

######################################################################

class LabelPosition(Enum):
    """Position of the label of an element relative to its shape."""

    BOTTOM = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()
    CENTER = auto()
    TOP = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()

    def is_bottom(self) -> bool:
        """True if the label is positioned at the bottom."""
        values = [
            self.BOTTOM.value,
            self.BOTTOM_LEFT.value,
            self.BOTTOM_RIGHT.value,
        ]
        return self.value in values

    def is_left(self) -> bool:
        """True if the label is positioned at the left side."""
        values = [
            self.BOTTOM_LEFT.value,
            self.TOP_LEFT.value,
        ]
        return self.value in values

    def is_right(self) -> bool:
        """True if the label is positioned at the right side."""
        values = [
            self.BOTTOM_RIGHT.value,
            self.TOP_RIGHT.value,
        ]
        return self.value in values

    def is_top(self) -> bool:
        """True if the label is positioned at the top."""
        values = [
            self.TOP.value,
            self.TOP_LEFT.value,
            self.TOP_RIGHT.value,
        ]
        return self.value in values

######################################################################

class Attributes(Mapping[str, Any]):
    """Collection of attributes."""

    # Catalog of valid attribute names.
    _attribute_names = set([
        'arrow_aspect',
        'arrow_back',
        'arrow_base',
        'arrow_forward',
        'buffer_fill',
        'buffer_width',
        'collapse_connections',
        'connection_distance',
        'entrances',
        'exits',
        'fill',
        'font_family',
        'font_size',
        'font_style',
        'font_weight',
        'label',
        'label_distance',
        'label_position',
        'margin_bottom',
        'margin_left',
        'margin_right',
        'margin_top',
        'min_height',
        'min_width',
        'padding_bottom',
        'padding_left',
        'padding_right',
        'padding_top',
        'pass_through',
        'stretch',
        'stroke_dasharray',
        'stroke_width',
        'stroke',
        'text_fill',
        'text_line_height',
        'text_orientation',
    ])

    def __init__(self, **attrs: AttributeMap):
        """Initialize the collection."""
        attributes: Dict[str, Any] = {}
        for key, value in attrs.items():
            attributes[key] = value
        self._attributes = attributes

    def __getitem__(self, key: str) -> Any:
        """Retrieve the value of an attribute."""
        return self._attributes[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set the value of the attribute."""
        self._attributes[key] = value

    def __iter__(self) -> Iterator[str]:
        """Return an iterator over the attribute names."""
        yield from self._attributes

    def __len__(self) -> int:
        """Return the number of attributes in the collection."""
        return len(self._attributes)

    def merge(self, src: AttributeMap) -> None:
        """Merge attributes to this instance."""
        names = self._attribute_names
        dest = self._attributes
        for key, value in src.items():
            if key in names:
                dest[key] = value

    def copy(self) -> 'Attributes':
        """Return a copy of self."""
        attrs: Dict[str, Any] = {}
        for key, value in self._attributes.items():
            attrs[key] = value
        return self.__class__(**attrs)

    def _pretty_print(self) -> None:
        """Print the attributes for debugging purposes."""
        print("Attributes:")
        for name in sorted(self._attribute_names):
            if name in self:
                print("\t{}: {}".format(name, self[name]))

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
        """Color of the line (e.g. "black")."""
        return self._stroke

    @property
    def stroke_dasharray(self) -> Optional[str]:
        """Dash pattern of the line (e.g. "4 4")."""
        return self._stroke_dasharray

    @property
    def stroke_width(self) -> float:
        """Width of the line (in pt)."""
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
        """Color of the interior (e.g. "white")."""
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
        """Initialize the attributes with default values."""
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
        """Font family of text (e.g. "sans")."""
        return self._font_family

    @property
    def font_size(self) -> float:
        """Font size of text (in pt)."""
        return self._font_size

    @property
    def font_style(self) -> Optional[str]:
        """Font style of text (e.g. "italic")."""
        return self._font_style

    @property
    def font_weight(self) -> Optional[str]:
        """Font weight of text (e.g. "bold")."""
        return self._font_weight

    @property
    def label(self) -> Optional[str]:
        """Text to draw on the element."""
        return self._label

    @property
    def text_fill(self) -> Optional[str]:
        """Color of text (e.g. "black")."""
        return self._text_fill

    @property
    def text_line_height(self) -> float:
        """Height of text line (in em)."""
        return self._text_line_height

    @property
    def text_orientation(self) -> Orientation:
        """Orientation of the text."""
        return self._text_orientation

######################################################################

class ContainerAttributes(LineAttributes, AreaAttributes, TextAttributes):
    """Collection of attributes relevant to containers."""

    def __init__(self) -> None:
        """Initialize the attributes with default values."""
        LineAttributes.__init__(self)
        AreaAttributes.__init__(self)
        TextAttributes.__init__(self)
        self._label_distance = 0.0
        self._label_position = LabelPosition.TOP
        self._padding_bottom = 0.0
        self._padding_left = 0.0
        self._padding_right = 0.0
        self._padding_top = 0.0

    def _set_container_attributes(self, attrs: AttributeMap) -> None:
        """Set the container attributes to the given values."""
        self._set_line_attributes(attrs)
        self._set_area_attributes(attrs)
        self._set_text_attributes(attrs)
        if 'label_distance' in attrs:
            self._label_distance = cast(float, attrs['label_distance'])
        if 'label_position' in attrs:
            self._label_position = cast(LabelPosition, attrs['label_position'])
        if 'padding_bottom' in attrs:
            self._padding_bottom = cast(float, attrs['padding_bottom'])
        if 'padding_left' in attrs:
            self._padding_left = cast(float, attrs['padding_left'])
        if 'padding_right' in attrs:
            self._padding_right = cast(float, attrs['padding_right'])
        if 'padding_top' in attrs:
            self._padding_top = cast(float, attrs['padding_top'])

    @property
    def label_distance(self) -> float:
        """Distance of the label from the border."""
        return self._label_distance

    @property
    def label_position(self) -> LabelPosition:
        """Position of the label."""
        return self._label_position

    @property
    def padding_bottom(self) -> float:
        """Distance between the contents and the bottom border."""
        return self._padding_bottom

    @property
    def padding_left(self) -> float:
        """Distance between the contents and the left border."""
        return self._padding_left

    @property
    def padding_right(self) -> float:
        """Distance between the contents and the right border."""
        return self._padding_right

    @property
    def padding_top(self) -> float:
        """Distance between the contents and the top border."""
        return self._padding_top

######################################################################

class BlockAttributes(ContainerAttributes):
    """Collection of attributes relevant to blocks."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the attributes with the given values."""
        ContainerAttributes.__init__(self)
        self._label_distance = 2.0
        self._label_position = LabelPosition.CENTER
        self._margin_bottom = 24.0
        self._margin_left = 24.0
        self._margin_right = 24.0
        self._margin_top = 24.0
        self._min_height = 48.0
        self._min_width = 96.0
        self._name: Optional[str] = None
        self._padding_bottom = 8.0
        self._padding_left = 8.0
        self._padding_right = 8.0
        self._padding_top = 8.0
        self._pass_through = False
        self.set_attributes(**attrs)

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        self._set_container_attributes(attrs)
        self._set_block_attributes(attrs)

    def _set_block_attributes(self, attrs: AttributeMap) -> None:
        """Set the attributes of the block to the given values."""
        if 'margin_bottom' in attrs:
            self._margin_bottom = cast(float, attrs['margin_bottom'])
        if 'margin_left' in attrs:
            self._margin_left = cast(float, attrs['margin_left'])
        if 'margin_right' in attrs:
            self._margin_right = cast(float, attrs['margin_right'])
        if 'margin_top' in attrs:
            self._margin_top = cast(float, attrs['margin_top'])
        if 'name' in attrs:
            self._name = cast(str, attrs['name'])
        if 'pass_through' in attrs:
            self._pass_through = cast(bool, attrs['pass_through'])

    @property
    def margin_bottom(self) -> float:
        """Margin under the shape."""
        return self._margin_bottom

    @property
    def margin_left(self) -> float:
        """Margin left of the shape."""
        return self._margin_left

    @property
    def margin_right(self) -> float:
        """Margin right of the shape."""
        return self._margin_right

    @property
    def margin_top(self) -> float:
        """Margin over the shape."""
        return self._margin_top

    @property
    def name(self) -> Optional[str]:
        """Name of the block."""
        return self._name

    @property
    def pass_through(self) -> bool:
        """Can a connection pass through the block?"""
        return self._pass_through

######################################################################

class ConnectionAttributes(LineAttributes):
    """Collection of attributes relevant to connections."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the attributes with the given values."""
        LineAttributes.__init__(self)
        all_sides = set([Side.BOTTOM, Side.LEFT, Side.RIGHT, Side.TOP])
        self._arrow_aspect = 1.5
        self._arrow_back = False
        self._arrow_base = 3.0
        self._arrow_forward = True
        self._buffer_fill: Optional[str] = None
        self._buffer_width: Optional[float] = None
        self._entrances: Set[Side] = all_sides
        self._exits: Set[Side] = all_sides
        self._stroke = "black"
        self.set_attributes(**attrs)

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        self._set_line_attributes(attrs)
        self._set_connection_attributes(attrs)

    def _set_connection_attributes(self, attrs: AttributeMap) -> None:
        """Set the connection attributes to the given values."""
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
        if 'entrances' in attrs:
            self._entrances = set(cast(Iterable[Side], attrs['entrances']))
        if 'exits' in attrs:
            self._exits = set(cast(Iterable[Side], attrs['exits']))

    @property
    def arrow_aspect(self) -> float:
        """Arrow aspect, length/width."""
        return self._arrow_aspect

    @property
    def arrow_back(self) -> bool:
        """Draw an arrow at the start of the connection?"""
        return self._arrow_back

    @property
    def arrow_base(self) -> float:
        """Multiply stroke width with this to get arrow base width."""
        return self._arrow_base

    @property
    def arrow_forward(self) -> bool:
        """Draw an arrow at the end of the connection?"""
        return self._arrow_forward

    @property
    def buffer_fill(self) -> Optional[str]:
        """Color of the buffer around the connection."""
        return self._buffer_fill

    @property
    def buffer_width(self) -> Optional[float]:
        """Width of the buffer around the connection."""
        return self._buffer_width

    @property
    def entrances(self) -> Set[Side]:
        """Sides to enter into the destination block."""
        return self._entrances

    @property
    def exits(self) -> Set[Side]:
        """Sides to exit from the source block."""
        return self._exits

######################################################################

class DiagramAttributes(ContainerAttributes):
    """Collection of attributes relevant to diagrams."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the attributes with the given values."""
        ContainerAttributes.__init__(self)
        self._collapse_connections = False
        self._connection_distance = 4.0
        self._font_size = 14.0
        self._label_distance = 6.0
        self._min_height = 300.0
        self._min_width = 300.0
        self._stretch = True
        self._stroke_width = 0.0
        self.set_attributes(**attrs)

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        self._set_container_attributes(attrs)
        self._set_diagram_attributes(attrs)

    def _set_diagram_attributes(self, attrs: AttributeMap) -> None:
        """Set the diagram attributes to the given values."""
        if 'collapse_connections' in attrs:
            self._collapse_connections = cast(
                bool, attrs['collapse_connections'])
        if 'connection_distance' in attrs:
            self._connection_distance = cast(
                float, attrs['connection_distance'])
        if 'stretch' in attrs:
            self._stretch = cast(bool, attrs['stretch'])

    @property
    def collapse_connections(self) -> bool:
        """Let connections that belong to the same group overlap?."""
        return self._collapse_connections

    @property
    def connection_distance(self) -> float:
        """Distance between connections."""
        return self._connection_distance

    @property
    def stretch(self) -> bool:
        """Stretch diagram to fill container?"""
        return self._stretch
