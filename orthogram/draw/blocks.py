"""Provides classes for drawing blocks."""

from typing import (
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
)

from cassowary.expression import Constraint # type: ignore

from ..define import Block, BlockAttributes

from .bands import Band
from .connections import Lane
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
            lane_margin: float = 0.0,
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
        self._lane_margin = lane_margin
        self._horizontal_lanes: List[Lane] = []
        self._vertical_lanes: List[Lane] = []

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

    def add_horizontal_lanes(self, lanes: Iterable[Lane]) -> None:
        """Associate the box with horizontal lanes connected to it."""
        self._horizontal_lanes.extend(lanes)

    def add_vertical_lanes(self, lanes: Iterable[Lane]) -> None:
        """Associate the box with vertical lanes connected to it."""
        self._vertical_lanes.extend(lanes)

    def constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the solver."""
        # Note that we do not need to introduce size constraints from
        # superclass here, since reference constraints guarantee their
        # satisfaction.
        yield from self._ref_constraints()
        yield from self._label_constraints()
        yield from self._lane_constraints()
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

    def _attributes(self) -> BlockAttributes:
        """Attributes of the block."""
        return self._block.attributes

    def _lane_constraints(self) -> Iterator[Constraint]:
        """Generate constraints to fit the connected lanes."""
        lanes = self._sorted_lanes(self._horizontal_lanes)
        margin = self._lane_margin
        if lanes:
            lane = lanes[0]
            yield self._ymin <= lane.cmin + lane.margin_before - margin
            lane = lanes[-1]
            yield self._ymax >= lane.cmax - lane.margin_after + margin
        lanes = self._sorted_lanes(self._vertical_lanes)
        if lanes:
            lane = lanes[0]
            yield self._xmin <= lane.cmin + lane.margin_before - margin
            lane = lanes[-1]
            yield self._xmax >= lane.cmax - lane.margin_after + margin

    @staticmethod
    def _sorted_lanes(lanes: Iterable[Lane]) -> Sequence[Lane]:
        """Sort lanes according to their order in the drawing."""
        key = lambda lane: lane.sort_key
        return sorted(lanes, key=key)

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
