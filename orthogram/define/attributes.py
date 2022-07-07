"""Provides means to collect and merge attributes."""

from enum import Enum, IntEnum, auto

from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    cast,
)

from ..util import (
    class_str,
    indent,
)

######################################################################

# Attributes are key-value pairs, where the key is a string.
AttributeMap = Mapping[str, Any]

######################################################################

class Side(IntEnum):
    """Block sides."""
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()

######################################################################

class TextOrientation(Enum):
    """Orientation of labels."""
    HORIZONTAL = auto()
    VERTICAL = auto()
    FOLLOW = auto()

######################################################################

class FontStyle(Enum):
    """Font styles."""
    NORMAL = auto()
    ITALIC = auto()
    OBLIQUE = auto()

class FontWeight(Enum):
    """Font weights."""
    NORMAL = auto()
    BOLD = auto()

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

class Color:
    """Color to draw shapes in."""

    def __init__(self, r: float, g: float, b: float, a: float = 1.0):
        """Initialize with the given values for the components."""
        self._red = r
        self._green = g
        self._blue = b
        self._alpha = a

    def __repr__(self) -> str:
        """Represent as string."""
        cls = self.__class__.__name__
        r = self._red
        g = self._green
        b = self._blue
        a = self._alpha
        return f"{cls}({r}, {g}, {b}, {a})"

    @property
    def red(self) -> float:
        """Red component."""
        return self._red

    @property
    def green(self) -> float:
        """Green component."""
        return self._green

    @property
    def blue(self) -> float:
        """Blue component."""
        return self._blue

    @property
    def alpha(self) -> float:
        """Alpha (opacity) component."""
        return self._alpha

    @property
    def rgba(self) -> Tuple[float, float, float, float]:
        """RGBA components in order."""
        return (self._red, self._green, self._blue, self._alpha)

    @classmethod
    def black(cls) -> 'Color':
        """Color object corresponding to black."""
        return cls(0.0, 0.0, 0.0)

    @classmethod
    def white(cls) -> 'Color':
        """Color object corresponding to white."""
        return cls(1.0, 1.0, 1.0)

######################################################################

# Type of stroke dash array values.
DashArray = List[float]

######################################################################

class Attributes(Mapping[str, Any]):
    """Collection of attributes."""

    # Catalog of valid attribute names.
    _attribute_names = [
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
        'scale',
        'stroke',
        'stroke_dasharray',
        'stroke_width',
        'text_fill',
        'text_line_height',
        'text_orientation',
    ]

    def __init__(self, **attrs: AttributeMap):
        """Initialize the collection with the given values."""
        attributes: Dict[str, Any] = {}
        for name in self._attribute_names:
            if name in attrs:
                attributes[name] = attrs[name]
        self._attributes = attributes

    def __getitem__(self, key: str) -> Any:
        """Retrieve the value of an attribute."""
        return self._attributes[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set the value of an attribute."""
        self._attributes[key] = value

    def __iter__(self) -> Iterator[str]:
        """Iterate over the attribute names."""
        yield from self._attributes

    def __len__(self) -> int:
        """Return the number of attributes in the collection."""
        return len(self._attributes)

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr({**self})
        return class_str(self, content)

    def merge(self, src: AttributeMap) -> None:
        """Merge attributes to this instance."""
        dest = self._attributes
        for name in self._attribute_names:
            if name in src:
                dest[name] = src[name]

    def _pretty_print(self) -> None:
        """Print the attributes for debugging purposes."""
        print("Attributes:")
        ind = indent(1)
        for name in sorted(self._attribute_names):
            if name in self:
                value = self[name]
                print(f"{ind}{name}: {value}")

######################################################################

class AttributesBackstop:
    """Last in the MRO of attribute classes."""

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Does nothing.

        This is necessary so that the calls to super from the child
        classes do not propagate to object.

        """

######################################################################

class LineAttributes(AttributesBackstop):
    """Collection of attributes relevant to linear objects."""

    def __init__(self) -> None:
        """Initialize with default attributes."""
        super().__init__()
        self._stroke: Optional[Color] = Color.black()
        self._stroke_dasharray: Optional[DashArray] = None
        self._stroke_width = 2.0

    @property
    def stroke(self) -> Optional[Color]:
        """Color of the line."""
        return self._stroke

    @property
    def stroke_dasharray(self) -> Optional[DashArray]:
        """Dash pattern of the line."""
        dashes = self._stroke_dasharray
        if dashes:
            return list(dashes)
        return None

    @property
    def stroke_width(self) -> float:
        """Width of the line."""
        return self._stroke_width

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        super().set_attributes(**attrs)
        if 'stroke' in attrs:
            self._stroke = cast(Optional[Color], attrs['stroke'])
        if 'stroke_dasharray' in attrs:
            self._stroke_dasharray = cast(Optional[DashArray],
                                          attrs['stroke_dasharray'])
        if 'stroke_width' in attrs:
            self._stroke_width = cast(float, attrs['stroke_width'])

######################################################################

class AreaAttributes(LineAttributes):
    """Collection of attributes relevant to 2D shapes."""

    def __init__(self) -> None:
        """Initialize with default attributes."""
        super().__init__()
        self._fill: Optional[Color] = None
        self._min_height = 0.0
        self._min_width = 0.0

    @property
    def fill(self) -> Optional[Color]:
        """Color of the interior."""
        return self._fill

    @property
    def min_height(self) -> float:
        """Minimum height of the shape."""
        return self._min_height

    @property
    def min_width(self) -> float:
        """Minimum width of the shape."""
        return self._min_width

    def set_attributes(self, ** attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        super().set_attributes(**attrs)
        if 'fill' in attrs:
            self._fill = cast(Optional[Color], attrs['fill'])
        if 'min_height' in attrs:
            self._min_height = cast(float, attrs['min_height'])
        if 'min_width' in attrs:
            self._min_width = cast(float, attrs['min_width'])

######################################################################

class TextAttributes(AttributesBackstop):
    """Collection of attributes relevant to text."""

    def __init__(self) -> None:
        """Initialize with default attributes."""
        super().__init__()
        self._font_family = "Arial"
        self._font_size = 10.0
        self._font_style = FontStyle.NORMAL
        self._font_weight = FontWeight.NORMAL
        self._label: Optional[str] = None
        self._label_distance = 0.0
        self._text_fill: Optional[Color] = Color.black()
        self._text_line_height = 1.2
        self._text_orientation = TextOrientation.HORIZONTAL

    @property
    def font_family(self) -> str:
        """Font family of text (e.g. "sans")."""
        return self._font_family

    @property
    def font_size(self) -> float:
        """Font size of text (in pt)."""
        return self._font_size

    @property
    def font_style(self) -> FontStyle:
        """Font style of text (e.g. ITALIC)."""
        return self._font_style

    @property
    def font_weight(self) -> FontWeight:
        """Font weight of text (e.g. BOLD)."""
        return self._font_weight

    @property
    def label(self) -> Optional[str]:
        """Text to draw on the element."""
        return self._label

    @property
    def label_distance(self) -> float:
        """Distance of the label from the border of the shape."""
        return self._label_distance

    @property
    def text_fill(self) -> Optional[Color]:
        """Color of text."""
        return self._text_fill

    @property
    def text_line_height(self) -> float:
        """Height of text line (in em)."""
        return self._text_line_height

    @property
    def text_orientation(self) -> TextOrientation:
        """Orientation of the text."""
        return self._text_orientation

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        super().set_attributes(**attrs)
        if 'font_family' in attrs:
            self._font_family = cast(str, attrs['font_family'])
        if 'font_size' in attrs:
            self._font_size = cast(float, attrs['font_size'])
        if 'font_style' in attrs:
            self._font_style = cast(FontStyle, attrs['font_style'])
        if 'font_weight' in attrs:
            self._font_weight = cast(FontWeight, attrs['font_weight'])
        if 'label' in attrs:
            self._label = cast(Optional[str], attrs['label'])
        if 'label_distance' in attrs:
            self._label_distance = cast(float, attrs['label_distance'])
        if 'text_fill' in attrs:
            self._text_fill = cast(Optional[Color], attrs['text_fill'])
        if 'text_line_height' in attrs:
            self._text_line_height = cast(float, attrs['text_line_height'])
        if 'text_orientation' in attrs:
            self._text_orientation = cast(
                TextOrientation, attrs['text_orientation'])

    def text_attributes_as_map(self) -> AttributeMap:
        """Return the text attributes as a mapping."""
        return {
            'font_family': self._font_family,
            'font_size': self._font_size,
            'font_style': self._font_style,
            'font_weight': self._font_weight,
            'label': self._label,
            'label_distance': self._label_distance,
            'text_fill': self._text_fill,
            'text_line_height': self._text_line_height,
            'text_orientation': self._text_orientation,
        }

######################################################################

class LabelAttributes(TextAttributes):
    """Collection of attributes relevant to labels."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the attributes with the given values."""
        super().__init__()
        self.set_attributes(**attrs)

######################################################################

class ContainerAttributes(AreaAttributes, TextAttributes):
    """Collection of attributes relevant to containers."""

    def __init__(self) -> None:
        """Initialize with default attributes."""
        super().__init__()
        self._label_distance = 6.0
        self._label_position = LabelPosition.TOP
        self._padding_bottom = 0.0
        self._padding_left = 0.0
        self._padding_right = 0.0
        self._padding_top = 0.0

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

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        super().set_attributes(**attrs)
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

######################################################################

class BlockAttributes(ContainerAttributes):
    """Collection of attributes relevant to diagram blocks."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the attributes with the given values."""
        super().__init__()
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

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        super().set_attributes(**attrs)
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

######################################################################

class ConnectionAttributes(LineAttributes, TextAttributes):
    """Collection of attributes relevant to connections."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the attributes with the given values."""
        super().__init__()
        all_sides = [Side.BOTTOM, Side.LEFT, Side.RIGHT, Side.TOP]
        self._arrow_aspect = 1.5
        self._arrow_back = False
        self._arrow_base = 3.0
        self._arrow_forward = True
        self._buffer_fill: Optional[Color] = None
        self._buffer_width = 0.0
        self._entrances = self._collect_sides(all_sides)
        self._exits = self._collect_sides(all_sides)
        self._label_distance = 2.0
        self._text_orientation = TextOrientation.FOLLOW
        self.set_attributes(**attrs)

    @staticmethod
    def _collect_sides(value: Any) -> List[Side]:
        """Return a collection of sorted unique block sides.

        Works with attribute values as well.

        """
        sides = cast(Iterable[Side], value)
        return sorted(set(sides))

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
    def buffer_fill(self) -> Optional[Color]:
        """Color of the buffer around the connection."""
        return self._buffer_fill

    @property
    def buffer_width(self) -> float:
        """Width of the buffer around the connection."""
        return self._buffer_width

    @property
    def entrances(self) -> List[Side]:
        """Sides to enter into the destination block."""
        return list(self._entrances)

    @property
    def exits(self) -> List[Side]:
        """Sides to exit from the source block."""
        return list(self._exits)

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        super().set_attributes(**attrs)
        if 'arrow_aspect' in attrs:
            self._arrow_aspect = cast(float, attrs['arrow_aspect'])
        if 'arrow_back' in attrs:
            self._arrow_back = cast(bool, attrs['arrow_back'])
        if 'arrow_base' in attrs:
            self._arrow_base = cast(float, attrs['arrow_base'])
        if 'arrow_forward' in attrs:
            self._arrow_forward = cast(bool, attrs['arrow_forward'])
        if 'buffer_fill' in attrs:
            self._buffer_fill = cast(Optional[Color], attrs['buffer_fill'])
        if 'buffer_width' in attrs:
            self._buffer_width = cast(float, attrs['buffer_width'])
        if 'entrances' in attrs:
            self._entrances = self._collect_sides(attrs['entrances'])
        if 'exits' in attrs:
            self._exits = self._collect_sides(attrs['exits'])

######################################################################

class DiagramAttributes(ContainerAttributes):
    """Collection of attributes relevant to diagrams."""

    def __init__(self, **attrs: AttributeMap):
        """Initialize the attributes with the given values."""
        super().__init__()
        self._collapse_connections = False
        self._connection_distance = 4.0
        self._fill = Color.white()
        self._font_size = 14.0
        self._min_height = 256.0
        self._min_width = 256.0
        self._scale = 1.0
        self._stroke = None
        self._stroke_width = 0.0
        self.set_attributes(**attrs)

    @property
    def collapse_connections(self) -> bool:
        """Let connections that belong to the same group merge?"""
        return self._collapse_connections

    @property
    def connection_distance(self) -> float:
        """Distance between connections."""
        return self._connection_distance

    @property
    def scale(self) -> float:
        """Scale drawing using this value."""
        return self._scale

    def set_attributes(self, **attrs: AttributeMap) -> None:
        """Set the attributes to the given values."""
        super().set_attributes(**attrs)
        if 'collapse_connections' in attrs:
            self._collapse_connections = cast(
                bool, attrs['collapse_connections'])
        if 'connection_distance' in attrs:
            self._connection_distance = cast(
                float, attrs['connection_distance'])
        if 'scale' in attrs:
            self._scale = cast(float, attrs['scale'])
