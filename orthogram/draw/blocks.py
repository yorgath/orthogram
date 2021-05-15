"""Provides classes for drawing blocks."""

from typing import (
    Iterable,
    Iterator,
    List,
    Optional,
)

from cassowary.expression import Constraint # type: ignore

from ..define import Block, BlockAttributes

from .bands import Band
from .connections import DrawingWireSegment
from .containers import Container
from .labels import Label

######################################################################

class BlockBox(Container):
    """Defines the extents of a block box in the drawing."""

    def __init__(
            self,
            index: int,
            block: Block,
            top_row: Band, bottom_row: Band,
            left_column: Band, right_column: Band,
            wire_margin: float = 0.0,
            label: Optional[Label] = None,
    ):
        """Initialize for a diagram block inside the given grid lines."""
        block_name = block.name
        name = f"box_{index}_{block_name}"
        super().__init__(name, label)
        self._block = block
        self._top_row = top_row
        self._bottom_row = bottom_row
        self._left_column = left_column
        self._right_column = right_column
        self._wire_margin = wire_margin
        self._connected_segments: List[DrawingWireSegment] = []

    def _attributes(self) -> BlockAttributes:
        """Attributes of the block."""
        return self._block.attributes

    @property
    def block(self) -> Block:
        """The block for which the box has been created."""
        return self._block

    @property
    def top_row(self) -> Band:
        """First row of the box."""
        return self._top_row

    @property
    def bottom_row(self) -> Band:
        """Last row of the box."""
        return self._bottom_row

    @property
    def left_column(self) -> Band:
        """First column of the box."""
        return self._left_column

    @property
    def right_column(self) -> Band:
        """Last column of the box."""
        return self._right_column

    def connect_segment(self, segment: DrawingWireSegment) -> None:
        """Connect the drawing segment to the box."""
        segments = self._connected_segments
        if segment not in segments:
            segments.append(segment)

    def constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the solver."""
        # Note that we do not need to introduce size constraints from
        # superclass here, since reference constraints guarantee their
        # satisfaction.
        yield from self._ref_constraints()
        yield from self._label_constraints()
        yield from self._wire_constraints()
        yield from self._band_constraints()

    def _ref_constraints(self) -> Iterable[Constraint]:
        """Generate constraints related to the reference lines."""
        attrs = self._attributes()
        half_width = 0.5 * attrs.min_width
        half_height = 0.5 * attrs.min_height
        yield self._ymin <= self._top_row.cref - half_height
        yield self._ymax >= self._bottom_row.cref + half_height
        yield self._xmin <= self._left_column.cref - half_width
        yield self._xmax >= self._right_column.cref + half_width

    def _wire_constraints(self) -> Iterator[Constraint]:
        """Generate constraints to fit the connected wires."""
        gap = self._wire_margin
        for seg in self._connected_segments:
            half_width = 0.5 * seg.wire_width + gap
            if seg.is_horizontal():
                y_wire = seg.start.y
                yield self._ymin <= y_wire - half_width
                yield self._ymax >= y_wire + half_width
            else:
                x_wire = seg.start.x
                yield self._xmin <= x_wire - half_width
                yield self._xmax >= x_wire + half_width

    def _band_constraints(self) -> Iterable[Constraint]:
        """Generate constraints to fit in the rows and columns."""
        attrs = self._block.attributes
        yield self._ymin >= self._top_row.track.cmin + attrs.margin_top
        yield self._ymax <= self._bottom_row.track.cmax - attrs.margin_bottom
        yield self._xmin >= self._left_column.track.cmin + attrs.margin_left
        yield self._xmax <= self._right_column.track.cmax - attrs.margin_right

    def optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the solver."""
        # Try not to grow beyond the minimum dimensions, if possible.
        attrs = self._attributes()
        half_width = 0.5 * attrs.min_width
        half_height = 0.5 * attrs.min_height
        yield self._ymin == self._top_row.cref - half_height
        yield self._ymax == self._bottom_row.cref + half_height
        yield self._xmin == self._left_column.cref - half_width
        yield self._xmax == self._right_column.cref + half_width
