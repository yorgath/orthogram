"""Provides classes for rectangular drawing elements."""

from typing import (
    Iterator,
    Optional,
)

from cassowary import Variable  # type: ignore
from cassowary.expression import Constraint  # type: ignore

from shapely.geometry import Polygon  # type: ignore

from ..define import (
    ContainerAttributes,
    DiagramAttributes,
    TextOrientation,
)

from ..geometry import Orientation
from ..util import class_str

from .labels import DrawingLabel

######################################################################

class Box:
    """Rectangular object that may contain other objects."""

    def __init__(
            self,
            attributes: ContainerAttributes,
            diagram_attributes: DiagramAttributes,
            name: str,
    ):
        """Initialize a box with the given name."""
        self._attributes = attributes
        self._diagram_attributes = diagram_attributes
        self._name = name
        self._label = self._make_label()
        self._xmin = Variable(f"{name}_xmin")
        self._xmax = Variable(f"{name}_xmax")
        self._ymin = Variable(f"{name}_ymin")
        self._ymax = Variable(f"{name}_ymax")

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._name)
        return class_str(self, content)

    @property
    def xmin(self) -> Variable:
        """Minimum coordinate along the X axis."""
        return self._xmin

    @property
    def xmax(self) -> Variable:
        """Maximum coordinate along the X axis."""
        return self._xmax

    @property
    def ymin(self) -> Variable:
        """Minimum coordinate along the Y axis."""
        return self._ymin

    @property
    def ymax(self) -> Variable:
        """Maximum coordinate along the Y axis."""
        return self._ymax

    @property
    def label(self) -> Optional[DrawingLabel]:
        """The label to draw on the box."""
        return self._label

    @property
    def attributes(self) -> ContainerAttributes:
        """Attributes of the box."""
        return self._attributes

    @property
    def padding_top(self) -> float:
        """Padding over the contents."""
        attrs = self.attributes
        pad = attrs.stroke_width + attrs.padding_top
        label = self._label
        if label and attrs.label_position.is_top():
            pad += attrs.label_distance + label.box_height
        return pad

    @property
    def padding_bottom(self) -> float:
        """Padding under the contents."""
        attrs = self.attributes
        pad = attrs.stroke_width + attrs.padding_bottom
        label = self._label
        if label and attrs.label_position.is_bottom():
            pad += attrs.label_distance + label.box_height
        return pad

    @property
    def padding_left(self) -> float:
        """Padding left of the contents."""
        attrs = self.attributes
        pad = attrs.stroke_width + attrs.padding_left
        return pad

    @property
    def padding_right(self) -> float:
        """Padding right of the contents."""
        attrs = self.attributes
        pad = attrs.stroke_width + attrs.padding_right
        return pad

    @property
    def polygon(self) -> Polygon:
        """Polygon geometry of the box."""
        xmin = self._xmin.value
        xmax = self._xmax.value
        ymin = self._ymin.value
        ymax = self._ymax.value
        points = [
            (xmin, ymin),
            (xmax, ymin),
            (xmax, ymax),
            (xmin, ymax),
            (xmin, ymin),
        ]
        return Polygon(points)

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the solver."""
        attrs = self._attributes
        width = max(attrs.min_width, self._width_for_label())
        height = max(attrs.min_height, self._height_for_label())
        yield self._xmax - self._xmin >= width
        yield self._ymax - self._ymin >= height

    def _width_for_label(self) -> float:
        """Width necessary for the label."""
        label = self._label
        if label:
            my_attrs = self.attributes
            label_attrs = label.attributes
            sides = 2 * (my_attrs.stroke_width + label_attrs.label_distance)
            width = label.box_width + sides
            return width
        return 0.0

    def _height_for_label(self) -> float:
        """Height necessary for the label."""
        label = self._label
        if label:
            my_attrs = self.attributes
            label_attrs = label.attributes
            sides = 2 * (my_attrs.stroke_width + label_attrs.label_distance)
            height = label.box_height + sides
            return height
        return 0.0

    def _make_label(self) -> Optional[DrawingLabel]:
        """Create a label to draw on the box."""
        attrs = self._attributes
        text = attrs.label
        if not text:
            return None
        tori = attrs.text_orientation
        if tori is TextOrientation.VERTICAL:
            ori = Orientation.VERTICAL
        else:
            ori = Orientation.HORIZONTAL
        return DrawingLabel(attrs, self._diagram_attributes, ori)
