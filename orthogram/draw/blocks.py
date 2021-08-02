"""Provides classes for drawing blocks."""

from dataclasses import dataclass

from typing import (
    Iterable,
    Iterator,
    List,
    Optional,
)

from cassowary import Variable  # type: ignore
from cassowary.expression import Constraint  # type: ignore

from shapely.geometry import Polygon  # type: ignore

from ..define import (
    Block,
    Side,
)

from ..util import class_str

from .bands import Band
from .connections import DrawingWireSegment
from .containers import Container
from .functions import arrow_length
from .labels import Label

######################################################################

@dataclass(frozen=True)
class Attachment:
    """Segment attached to a block."""
    segment: DrawingWireSegment
    side: Side
    out: bool

######################################################################

class BlockBox:
    """Defines the extents of a block box in the drawing."""

    def __init__(
            self,
            block: Block,
            top_row: Band, bottom_row: Band,
            left_column: Band, right_column: Band,
            wire_margin: float = 0.0,
            label: Optional[Label] = None,
    ):
        """Initialize for a diagram block inside the given grid lines."""
        self._block = block
        self._top_row = top_row
        self._bottom_row = bottom_row
        self._left_column = left_column
        self._right_column = right_column
        self._wire_margin = wire_margin
        var_prefix = f"block_{block.index}"
        self._container = Container(block.attributes, var_prefix, label)
        self._attachments: List[Attachment] = []

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._block.description()
        return class_str(self, content)

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

    ###################### Container delegates #######################

    @property
    def container(self) -> Container:
        """Return the container associated with this."""
        return self._container

    @property
    def xmin(self) -> Variable:
        """Minimum coordinate along the X axis."""
        return self._container.xmin

    @property
    def xmax(self) -> Variable:
        """Maximum coordinate along the X axis."""
        return self._container.xmax

    @property
    def ymin(self) -> Variable:
        """Minimum coordinate along the Y axis."""
        return self._container.ymin

    @property
    def ymax(self) -> Variable:
        """Maximum coordinate along the Y axis."""
        return self._container.ymax

    @property
    def padding_top(self) -> float:
        """Padding over the contents."""
        return self._container.padding_top

    @property
    def padding_bottom(self) -> float:
        """Padding under the contents."""
        return self._container.padding_bottom

    @property
    def padding_left(self) -> float:
        """Padding left of the contents."""
        return self._container.padding_left

    @property
    def padding_right(self) -> float:
        """Padding right of the contents."""
        return self._container.padding_right

    @property
    def polygon(self) -> Polygon:
        """Polygon geometry of the box."""
        return self._container.polygon

    ################### End of container delegates ###################

    def constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the solver."""
        # Note that we do not need to introduce size constraints from
        # superclass here, since reference constraints guarantee their
        # satisfaction.
        yield from self._ref_constraints()
        yield from self._container.label_constraints()
        yield from self._wire_constraints()
        yield from self._band_constraints()

    def optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the solver."""
        # Try not to grow beyond the minimum dimensions, if possible.
        attrs = self._block.attributes
        half_width = 0.5 * attrs.min_width
        half_height = 0.5 * attrs.min_height
        yield self.ymin == self._top_row.cref - half_height
        yield self.ymax == self._bottom_row.cref + half_height
        yield self.xmin == self._left_column.cref - half_width
        yield self.xmax == self._right_column.cref + half_width

    def attach_segment(
            self,
            segment: DrawingWireSegment,
            side: Side, out: bool,
    ) -> None:
        """Attach the drawing segment to the box."""
        attachments = self._attachments
        attachment = Attachment(segment=segment, side=side, out=out)
        if attachment in attachments:
            return
        attachments.append(attachment)

    def _ref_constraints(self) -> Iterable[Constraint]:
        """Generate constraints related to the reference lines."""
        attrs = self._block.attributes
        half_width = 0.5 * attrs.min_width
        half_height = 0.5 * attrs.min_height
        yield self.ymin <= self._top_row.cref - half_height
        yield self.ymax >= self._bottom_row.cref + half_height
        yield self.xmin <= self._left_column.cref - half_width
        yield self.xmax >= self._right_column.cref + half_width

    def _wire_constraints(self) -> Iterator[Constraint]:
        """Generate constraints to fit the attached wires."""
        gap = self._wire_margin
        for attachment in self._attachments:
            seg = attachment.segment
            half_width = 0.5 * seg.wire_width + gap
            if seg.is_horizontal():
                y_wire = seg.start.y
                yield self.ymin <= y_wire - half_width
                yield self.ymax >= y_wire + half_width
            else:
                x_wire = seg.start.x
                yield self.xmin <= x_wire - half_width
                yield self.xmax >= x_wire + half_width

    def _band_constraints(self) -> Iterable[Constraint]:
        """Generate constraints to fit in the rows and columns."""
        attrs = self._block.attributes
        # Top side.
        margin = self._calculate_margin(Side.TOP, attrs.margin_top)
        yield self.ymin >= self._top_row.track.cmin + margin
        # Bottom side.
        margin = self._calculate_margin(Side.BOTTOM, attrs.margin_bottom)
        yield self.ymax <= self._bottom_row.track.cmax - margin
        # Left side.
        margin = self._calculate_margin(Side.LEFT, attrs.margin_left)
        yield self.xmin >= self._left_column.track.cmin + margin
        # Right side.
        margin = self._calculate_margin(Side.RIGHT, attrs.margin_right)
        yield self.xmax <= self._right_column.track.cmax - margin

    def _calculate_margin(self, side: Side, min_margin: float) -> float:
        """Calculate the margin on the given side of the box."""
        margin = min_margin
        for attachment in self._attachments_on(side):
            seg_attrs = attachment.segment.attributes
            out = attachment.out
            if (
                    (out and seg_attrs.arrow_back) or
                    (not out and seg_attrs.arrow_forward)
            ):
                margin = max(margin, arrow_length(seg_attrs))
        return margin

    def _attachments_on(self, side: Side) -> Iterator[Attachment]:
        """Iterate over the attached segments on a block side."""
        for attachment in self._attachments:
            if attachment.side is side:
                yield attachment
