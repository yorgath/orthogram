"""Provides abstract base classes for container drawing elements."""

from abc import ABCMeta, abstractmethod

from typing import (
    Iterable,
    Optional,
)

from cassowary import Variable # type: ignore
from cassowary.expression import Constraint # type: ignore

from shapely.geometry import Polygon # type: ignore

from ..define import ContainerAttributes
from ..names import Named

from .labels import Label

######################################################################

class Container(Named, metaclass=ABCMeta):
    """Rectangular object that contains other objects."""

    def __init__(self, name: str, label: Optional[Label] = None):
        """Initialize a container with the given name."""
        super().__init__(name)
        self._label = label
        self._xmin = Variable(f"{name}_xmin")
        self._xmax = Variable(f"{name}_xmax")
        self._ymin = Variable(f"{name}_ymin")
        self._ymax = Variable(f"{name}_ymax")

    @property
    def label(self) -> Optional[Label]:
        """The label of the block inside the box."""
        return self._label

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
    def padding_top(self) -> float:
        """Padding over the contents."""
        attrs = self._attributes()
        pad = attrs.stroke_width + attrs.padding_top
        label = self._label
        if label and attrs.label_position.is_top():
            pad += attrs.label_distance + label.box_height
        return pad

    @property
    def padding_bottom(self) -> float:
        """Padding under the contents."""
        attrs = self._attributes()
        pad = attrs.stroke_width + attrs.padding_bottom
        label = self._label
        if label and attrs.label_position.is_bottom():
            pad += attrs.label_distance + label.box_height
        return pad

    @property
    def padding_left(self) -> float:
        """Margin if on the left side of the box."""
        attrs = self._attributes()
        pad = attrs.stroke_width + attrs.padding_left
        return pad

    @property
    def padding_right(self) -> float:
        """Margin if on the right side of the box."""
        attrs = self._attributes()
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

    def _size_constraints(self) -> Iterable[Constraint]:
        """Generate constraints to satisfy minimum dimensions."""
        attrs = self._attributes()
        yield self._xmax >= self._xmin + attrs.min_width
        yield self._ymax >= self._ymin + attrs.min_height

    def _label_constraints(self) -> Iterable[Constraint]:
        """Generate constraints to fit the label."""
        yield self._xmax >= self._xmin + self._width_for_label()
        yield self._ymax >= self._ymin + self._height_for_label()

    def _width_for_label(self) -> float:
        """Width necessary for the label."""
        label = self._label
        if label:
            attrs = self._attributes()
            sides = 2 * (attrs.stroke_width + attrs.label_distance)
            width = label.box_width + sides
            return width
        return 0.0

    def _height_for_label(self) -> float:
        """Height necessary for the label."""
        label = self._label
        if label:
            attrs = self._attributes()
            sides = 2 * (attrs.stroke_width + attrs.label_distance)
            height = label.box_height + sides
            return height
        return 0.0

    @property
    def attributes(self) -> ContainerAttributes:
        """Attributes of the diagram object."""
        return self._attributes()

    @abstractmethod
    def _attributes(self) -> ContainerAttributes:
        """Override this to return the attributes of the container."""
