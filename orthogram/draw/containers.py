"""Provides classes for container drawing elements."""

from typing import (
    Iterable,
    Optional,
)

from cassowary import Variable  # type: ignore
from cassowary.expression import Constraint  # type: ignore

from shapely.geometry import Polygon  # type: ignore

from ..define import ContainerAttributes
from ..util import class_str

from .labels import Label

######################################################################

class Container:
    """Rectangular object that contains other objects."""

    def __init__(
            self,
            attrs: ContainerAttributes,
            var_prefix: str,
            label: Optional[Label] = None,
    ):
        """Initialize a container with the given name."""
        self._attributes = attrs
        self._var_prefix = var_prefix
        self._label = label
        self._xmin = Variable(f"{var_prefix}_xmin")
        self._xmax = Variable(f"{var_prefix}_xmax")
        self._ymin = Variable(f"{var_prefix}_ymin")
        self._ymax = Variable(f"{var_prefix}_ymax")

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._var_prefix)
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
    def label(self) -> Optional[Label]:
        """The label to draw on the box."""
        return self._label

    @property
    def attributes(self) -> ContainerAttributes:
        """Attributes of the container."""
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

    def label_constraints(self) -> Iterable[Constraint]:
        """Generate constraints to fit the label."""
        yield self._xmax >= self._xmin + self._width_for_label()
        yield self._ymax >= self._ymin + self._height_for_label()

    def _width_for_label(self) -> float:
        """Width necessary for the label."""
        label = self._label
        if label:
            attrs = self.attributes
            sides = 2 * (attrs.stroke_width + attrs.label_distance)
            width = label.box_width + sides
            return width
        return 0.0

    def _height_for_label(self) -> float:
        """Height necessary for the label."""
        label = self._label
        if label:
            attrs = self.attributes
            sides = 2 * (attrs.stroke_width + attrs.label_distance)
            height = label.box_height + sides
            return height
        return 0.0
