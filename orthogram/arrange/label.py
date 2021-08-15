"""Arrange labels on the diagram."""

from enum import Enum, auto

from typing import (
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
)

from ..define import TextAttributes
from ..geometry import OrientedVector
from ..util import class_str

from .net import (
    Wire,
    WireSegment,
)

from .refine import Refiner

######################################################################

class ConnectionLabelPosition(Enum):
    """Position of a connection label relative to the connection."""
    START = auto()
    MIDDLE = auto()
    END = auto()

    def is_start(self) -> bool:
        """True if this is at the start of the connection."""
        return self is ConnectionLabelPosition.START

    def is_middle(self) -> bool:
        """True if this is at the middle of the connection."""
        return self is ConnectionLabelPosition.MIDDLE

    def is_end(self) -> bool:
        """True if this is at the end of the connection."""
        return self is ConnectionLabelPosition.END

######################################################################

class WireSegmentSpan:
    """Wire segment span between two grid coordinates."""

    def __init__(
            self,
            segment: WireSegment, index: int,
            coords: Tuple[int, int],
            is_first: bool, is_last: bool,
    ):
        """Initialize given the segment and the coordinates on it."""
        self._segment = segment
        self._index = index
        self._grid_vector = OrientedVector(segment.axis, coords)
        self._is_first = is_first
        self._is_last = is_last
        self._name = f"{segment.name}.{index}"

    def __repr__(self) -> str:
        """Represent as string."""
        name = self._name
        desc = self.internals_description()
        content = "f{name}, {desc}"
        return class_str(self, content)

    @property
    def segment(self) -> WireSegment:
        """The wire segment on which the span lies."""
        return self._segment

    @property
    def grid_vector(self) -> OrientedVector:
        """Vector between the two grid points."""
        return self._grid_vector

    def is_first(self) -> bool:
        """True if the span is first in the whole wire."""
        return self._is_first

    def is_last(self) -> bool:
        """True if the span is first in the whole wire."""
        return self._is_last

    @property
    def name(self) -> str:
        """A name for the span."""
        return self._name

    def internals_description(self) -> str:
        """Description of the internals of the object."""
        seg = self._segment
        ends = seg.connection.ends_description()
        dvec = self._grid_vector.vector_depiction()
        return f"{ends}, points={dvec}"

######################################################################

class WireLabel:
    """Label on a connection wire."""

    def __init__(
            self,
            span: WireSegmentSpan,
            position: ConnectionLabelPosition,
            text: str,
    ):
        """Initialize for a given segment span."""
        self._span = span
        self._position = position
        self._text = text
        self._name = f"{span.name}.{position.name}"

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    @property
    def segment(self) -> WireSegment:
        """The wire segment."""
        return self._span.segment

    @property
    def position(self) -> ConnectionLabelPosition:
        """Position of the label along the wire."""
        return self._position

    @property
    def text(self) -> str:
        """Text of the label."""
        return self._text

    @property
    def attributes(self) -> TextAttributes:
        """Attributes of the label."""
        return self.segment.connection.attributes

    @property
    def grid_vector(self) -> OrientedVector:
        """Vector between the two grid points."""
        return self._span.grid_vector

    def follows_segment(self) -> bool:
        """True if the orientation of the label matches that of the segment."""
        return self.segment.follows_label()

    @property
    def name(self) -> str:
        """A name for the object."""
        return self._name

    def description(self) -> str:
        """Description of the label object."""
        name = repr(self._name)
        span = self._span.internals_description()
        text = repr(self._text)
        return f"{name}, {span}, text={text}"

######################################################################

class Labeler:
    """Arrange labels on the layout grid."""

    def __init__(self, refiner: Refiner):
        """Initialize for a given layout refinement object."""
        self._refiner = refiner
        self._segment_map = refiner.router.segment_map()
        self._wire_labels = list(self._make_wire_labels())

    def wire_labels(self) -> Iterator[WireLabel]:
        """Iterate over the labels for the wires."""
        yield from self._wire_labels

    def _make_wire_labels(self) -> Iterator[WireLabel]:
        """Create the labels for the connection wires."""
        for wire in self._wires():
            yield from self._make_labels_for_wire(wire)

    def _wires(self) -> Iterator[Wire]:
        """Return the wires in drawing order."""
        for net in self._refiner.networks():
            yield from net.wires()

    def _make_labels_for_wire(self, wire: Wire) -> Iterator[WireLabel]:
        """Create the labels for the given wire."""
        spans = list(self._wire_spans_for_labels(wire))
        attrs = wire.connection.attributes
        Pos = ConnectionLabelPosition
        text = attrs.start_label
        if text:
            yield WireLabel(spans[0], Pos.START, text)
        text = attrs.label
        if text:
            span = self._span_for_middle_label(spans)
            yield WireLabel(span, Pos.MIDDLE, text)
        text = attrs.end_label
        if text:
            yield WireLabel(spans[-1], Pos.END, text)

    def _wire_spans_for_labels(self, wire: Wire) -> Iterator[WireSegmentSpan]:
        """Return the sub-segments on which labels can be placed."""
        for seg in wire.segments():
            yield from self._segment_spans_for_labels(seg)

    def _segment_spans_for_labels(
            self, segment: WireSegment
    ) -> Iterator[WireSegmentSpan]:
        """Return the sub-segments on which labels can be placed.

        These are calculated considering the intersections with other
        segments on the top/left side only, assuming this is the side
        where the labels are going to be placed.

        """
        axis = segment.axis
        stops_set = set(segment.min_max_coordinates)
        cuts = self._refiner.segment_intersections(segment)
        stops_set.update(cuts)
        stops = sorted(stops_set)
        # Create the spans along the direction of the segment.
        if segment.direction.is_descending():
            stops.reverse()
        segment_is_first = segment.is_first()
        segment_is_last = segment.is_last()
        last_index = len(stops) - 2
        for k, coord_1 in enumerate(stops[:-1]):
            coord_2 = stops[k + 1]
            is_first = segment_is_first and k == 0
            is_last = segment_is_last and k == last_index
            span = WireSegmentSpan(
                segment=segment, index=k,
                coords = (coord_1, coord_2),
                is_first=is_first, is_last=is_last
            )
            yield span

    @staticmethod
    def _span_for_middle_label(
            wire_spans: Iterable[WireSegmentSpan]
    ) -> WireSegmentSpan:
        """Return the optimal sub-segment for the middle label."""
        # Prefer segments with the same orientation as the label.
        spans = [span for span in wire_spans if span.segment.follows_label()]
        # However, we will take any segment if we have to.
        if not spans:
            spans = list(wire_spans)
        # Pick the longest sub-segment.
        key = lambda span: span.grid_vector.length
        spans.sort(key=key, reverse=True)
        return spans[0]
