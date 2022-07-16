"""Provides classes for drawing blocks."""

from dataclasses import dataclass

from typing import (
    Iterable,
    Iterator,
    List,
    Optional,
)

from cassowary.expression import Constraint  # type: ignore

from ..define import (
    Block,
    ConnectionLabelPosition,
    DiagramAttributes,
    Side,
)

from ..util import class_str

from .bands import Band

from .connections import (
    DrawingWireLabel,
    DrawingWireSegment,
)

from .boxes import Box
from .functions import arrow_length

######################################################################

@dataclass(frozen=True)
class Attachment:
    """Segment attached to a block."""
    segment: DrawingWireSegment
    side: Side
    out: bool

######################################################################

class DrawingBlock:
    """Drawing of a diagram block."""

    def __init__(
            self,
            diagram_block: Block,
            diagram_attributes: DiagramAttributes,
            top_row: Band, bottom_row: Band,
            left_column: Band, right_column: Band,
    ):
        """Initialize for a diagram block inside the given grid lines."""
        self._diagram_block = diagram_block
        self._diagram_attributes = diagram_attributes
        self._top_row = top_row
        self._bottom_row = bottom_row
        self._left_column = left_column
        self._right_column = right_column
        block_name = f"block_{diagram_block.index}"
        self._box = Box(
            diagram_block.attributes,
            diagram_attributes,
            block_name,
        )
        self._attachments: List[Attachment] = []

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._diagram_block.description()
        return class_str(self, content)

    @property
    def diagram_block(self) -> Block:
        """The diagram block for which this has been created."""
        return self._diagram_block

    @property
    def top_row(self) -> Band:
        """First grid row of the block."""
        return self._top_row

    @property
    def bottom_row(self) -> Band:
        """Last grid row of the block."""
        return self._bottom_row

    @property
    def left_column(self) -> Band:
        """First grid column of the block."""
        return self._left_column

    @property
    def right_column(self) -> Band:
        """Last grid column of the block."""
        return self._right_column

    @property
    def box(self) -> Box:
        """Return the box associated with this."""
        return self._box

    def constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the solver."""
        yield from self._box.constraints()
        yield from self._ref_constraints()
        yield from self._wire_constraints()
        yield from self._margin_constraints()
        yield from self._connection_label_constraints()

    def optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the solver."""
        # Try not to grow beyond the minimum dimensions, if possible.
        attrs = self._diagram_block.attributes
        half_width = 0.5 * attrs.min_width
        half_height = 0.5 * attrs.min_height
        box = self._box
        yield box.ymin == self._top_row.cref - half_height
        yield box.ymax == self._bottom_row.cref + half_height
        yield box.xmin == self._left_column.cref - half_width
        yield box.xmax == self._right_column.cref + half_width

    def attach_segment(
            self,
            segment: DrawingWireSegment,
            side: Side, out: bool,
    ) -> None:
        """Attach the segment to the block."""
        attachments = self._attachments
        attachment = Attachment(segment=segment, side=side, out=out)
        if attachment in attachments:
            return
        attachments.append(attachment)

    def _ref_constraints(self) -> Iterable[Constraint]:
        """Generate constraints related to the reference lines."""
        attrs = self._diagram_block.attributes
        half_width = 0.5 * attrs.min_width
        half_height = 0.5 * attrs.min_height
        box = self._box
        yield box.ymin <= self._top_row.cref - half_height
        yield box.ymax >= self._bottom_row.cref + half_height
        yield box.xmin <= self._left_column.cref - half_width
        yield box.xmax >= self._right_column.cref + half_width

    def _wire_constraints(self) -> Iterator[Constraint]:
        """Generate constraints to fit the attached wires."""
        box = self._box
        gap = self._diagram_attributes.connection_distance
        for attachment in self._attachments:
            seg = attachment.segment
            half_width = 0.5 * seg.wire_width + gap
            if seg.grid_vector.is_horizontal():
                y_wire = seg.start.y
                yield box.ymin <= y_wire - half_width
                yield box.ymax >= y_wire + half_width
            else:
                x_wire = seg.start.x
                yield box.xmin <= x_wire - half_width
                yield box.xmax >= x_wire + half_width

    def _margin_constraints(self) -> Iterable[Constraint]:
        """Generate constraints for the margins.

        These include the arrows, since they are drawn inside the
        margins.

        """
        box = self._box
        attrs = self._diagram_block.attributes
        # Top side.
        margin = self._calculate_margin(Side.TOP, attrs.margin_top)
        yield box.ymin >= self._top_row.cmin + margin
        # Bottom side.
        margin = self._calculate_margin(Side.BOTTOM, attrs.margin_bottom)
        yield box.ymax <= self._bottom_row.cmax - margin
        # Left side.
        margin = self._calculate_margin(Side.LEFT, attrs.margin_left)
        yield box.xmin >= self._left_column.cmin + margin
        # Right side.
        margin = self._calculate_margin(Side.RIGHT, attrs.margin_right)
        yield box.xmax <= self._right_column.cmax - margin

    def _calculate_margin(self, side: Side, min_margin: float) -> float:
        """Calculate the margin on the given side of the block."""
        # Start with minimum requested.
        margin = min_margin
        for attachment in self._attachments_on(side):
            # Make room the arrow, if any.
            seg_attrs = attachment.segment.attributes
            out = attachment.out
            if (
                    (out and seg_attrs.arrow_back) or
                    (not out and seg_attrs.arrow_forward)
            ):
                margin = max(margin, arrow_length(seg_attrs))
        return margin

    def _connection_label_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the attached connection labels."""
        box = self._box
        # Top side.
        for wire_label in self._labels_on(Side.TOP):
            dist = wire_label.attributes.label_distance
            yield box.ymin - wire_label.lmax == dist
            yield wire_label.lmin - self._top_row.cmin >= dist
        # Bottom side.
        for wire_label in self._labels_on(Side.BOTTOM):
            dist = wire_label.attributes.label_distance
            yield wire_label.lmin - box.ymax == dist
            yield self._bottom_row.cmax - wire_label.lmax >= dist
        # Left side.
        for wire_label in self._labels_on(Side.LEFT):
            dist = wire_label.attributes.label_distance
            yield box.xmin - wire_label.lmax == dist
            yield wire_label.lmin - self._left_column.cmin >= dist
        # Right side.
        for wire_label in self._labels_on(Side.RIGHT):
            dist = wire_label.attributes.label_distance
            yield wire_label.lmin - box.xmax == dist
            yield self._right_column.cmax - wire_label.lmax >= dist

    def _labels_on(self, side: Side) -> Iterator[DrawingWireLabel]:
        """Iterate over the connection labels on a block side."""
        for attachment in self._attachments_on(side):
            label = self._attached_label(attachment)
            if label:
                yield label

    def _attachments_on(self, side: Side) -> Iterator[Attachment]:
        """Iterate over the attached segments on a block side."""
        for attachment in self._attachments:
            if attachment.side is side:
                yield attachment

    @staticmethod
    def _attached_label(attachment: Attachment) -> Optional[DrawingWireLabel]:
        """Return the connection label next to the block."""
        Pos = ConnectionLabelPosition
        out = attachment.out
        for label in attachment.segment.labels():
            position = label.position
            if (
                    (out and position is Pos.START) or
                    (not out and position is Pos.END)
            ):
                return label
        return None
