"""Arrange labels on the diagram."""

from typing import (
    Iterable,
    Iterator,
    Tuple,
)

from ..define import (
    ConnectionLabelPosition,
    Label,
    TextAttributes,
    TextOrientation,
)

from ..geometry import (
    Orientation,
    OrientedVector,
)

from ..util import class_str

from .net import (
    Wire,
    WireSegment,
)

from .refine import Refiner

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
        self._grid_vector = OrientedVector(segment.grid_vector.axis, coords)
        self._is_first = is_first
        self._is_last = is_last
        self._name = f"{segment.name}.{index}"

    def __repr__(self) -> str:
        """Represent as string."""
        name = self._name
        desc = self.internals_description()
        content = f"{name}, {desc}"
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
        """True if the span is last in the whole wire."""
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
            diagram_label: Label,
            span: WireSegmentSpan,
            position: ConnectionLabelPosition,
    ):
        """Initialize for a given segment span."""
        self._diagram_label = diagram_label
        self._span = span
        self._position = position
        self._orientation = _label_orientation(diagram_label, span.segment)
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
    def orientation(self) -> Orientation:
        """Orientation of the label."""
        return self._orientation

    def follows_segment(self) -> bool:
        """True if the label and the segment have the same orientation."""
        return self.orientation is self.grid_vector.orientation

    @property
    def attributes(self) -> TextAttributes:
        """Attributes of the label."""
        return self._diagram_label.attributes

    @property
    def grid_vector(self) -> OrientedVector:
        """Vector between the two grid points."""
        return self._span.grid_vector

    @property
    def name(self) -> str:
        """A name for the object."""
        return self._name

    def description(self) -> str:
        """Description of the label object."""
        name = repr(self._name)
        span = self._span.internals_description()
        text = repr(self.attributes.label)
        return f"{name}, {span}, text={text}"

######################################################################

class Labeler:
    """Arrange labels on the layout grid."""

    def __init__(self, refiner: Refiner):
        """Initialize for a given layout refinement object."""
        self._refiner = refiner
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
        Pos = ConnectionLabelPosition
        # Start.
        dia_label = wire.connection.start_label
        if dia_label:
            yield WireLabel(dia_label, spans[0], Pos.START)
        # Middle.
        dia_label = wire.connection.middle_label
        if dia_label:
            span = _span_for_middle_label(dia_label, spans)
            yield WireLabel(dia_label, span, Pos.MIDDLE)
        # End.
        dia_label = wire.connection.end_label
        if dia_label:
            yield WireLabel(dia_label, spans[-1], Pos.END)

    def _wire_spans_for_labels(self, wire: Wire) -> Iterator[WireSegmentSpan]:
        """Return the sub-segments on which labels can be placed."""
        for seg in wire:
            yield from self._segment_spans_for_labels(seg)

    def _segment_spans_for_labels(
            self, segment: WireSegment
    ) -> Iterator[WireSegmentSpan]:
        """Return the sub-segments on which labels can be placed.

        These are calculated considering the intersections with other
        segments on the top/left side only, assuming this is the side
        where the labels are going to be placed.

        """
        vec = segment.grid_vector
        stops_set = set(vec.min_max_coordinates)
        cuts = self._refiner.segment_intersections(segment)
        stops_set.update(cuts)
        stops = sorted(stops_set)
        # Create the spans along the direction of the segment.
        if vec.direction.is_descending():
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
                coords=(coord_1, coord_2),
                is_first=is_first, is_last=is_last
            )
            yield span

######################################################################

def _span_for_middle_label(
        dia_label: Label,
        wire_spans: Iterable[WireSegmentSpan]
) -> WireSegmentSpan:
    """Return the optimal sub-segment for the middle label."""
    # Prefer segments with the same orientation as the label.
    spans = list(_preferred_spans_for_middle_label(dia_label, wire_spans))
    # However, we will take any segment if we have to.
    if not spans:
        spans = list(wire_spans)
    # Pick the longest sub-segment.
    key = lambda span: span.grid_vector.length
    spans.sort(key=key, reverse=True)
    return spans[0]

def _preferred_spans_for_middle_label(
        dia_label: Label,
        wire_spans: Iterable[WireSegmentSpan]
) -> Iterator[WireSegmentSpan]:
    """Return the spans preferred for middle label placement."""
    for span in wire_spans:
        segment = span.segment
        label_ori = _label_orientation(dia_label, segment)
        if label_ori is segment.grid_vector.orientation:
            yield span

def _label_orientation(dia_label: Label, segment: WireSegment) -> Orientation:
    """Return the orientation of the label when put on the given segment."""
    tori = dia_label.attributes.text_orientation
    if tori is TextOrientation.HORIZONTAL:
        return Orientation.HORIZONTAL
    if tori is TextOrientation.VERTICAL:
        return Orientation.VERTICAL
    return segment.grid_vector.orientation
