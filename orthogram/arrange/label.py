"""Arrange labels on the diagram."""

from typing import (
    Iterator,
    List,
    Optional,
    Sequence,
)

from ..geometry import OrientedVector
from ..util import class_str

from .net import (
    Wire,
    WireSegment,
)

from .refine import Refiner

######################################################################

class WireSegmentSpan:
    """Wire segment span between two grid coordinates."""

    def __init__(self, segment: WireSegment, min_coord: int, max_coord: int):
        """Initialize given the segment and the grid coordinates."""
        self._segment = segment
        self._min_coord = min_coord
        self._max_coord = max_coord

    def __repr__(self) -> str:
        """Represent as string."""
        content = self.description()
        return class_str(self, content)

    def __len__(self) -> int:
        """Length of the span."""
        return self._max_coord - self._min_coord + 1

    @property
    def segment(self) -> WireSegment:
        """The wire segment on which the span lies."""
        return self._segment

    @property
    def min_coord(self) -> int:
        """Minimum coordinate."""
        return self._min_coord

    @property
    def max_coord(self) -> int:
        """Maximum coordinate."""
        return self._max_coord

    def follows_label(self) -> bool:
        """True if the orientation of the segment matches that of the label."""
        return self._segment.route_segment.follows_label()

    def description(self) -> str:
        """Description of the object."""
        seg = self._segment
        name = seg.name
        ends = seg.connection.ends_description()
        vec = OrientedVector(seg.axis, (self._min_coord, self._max_coord))
        dvec = vec.vector_depiction()
        return f"{name}, {ends}, points={dvec}"

######################################################################

class WireLabel:
    """Label on a connection wire."""

    def __init__(self, wire: Wire, span: WireSegmentSpan):
        """Initialize for a given wire and segment span."""
        self._wire = wire
        self._span = span

    def __repr__(self) -> str:
        """Represent as string."""
        content = self._span.description()
        return class_str(self, content)

    @property
    def segment(self) -> WireSegment:
        """The wire segment."""
        return self._span.segment

    @property
    def min_coord(self) -> int:
        """Minimum coordinate."""
        return self._span.min_coord

    @property
    def max_coord(self) -> int:
        """Maximum coordinate."""
        return self._span.max_coord

######################################################################

class Labeler:
    """Arrange labels on the layout grid."""

    def __init__(self, refiner: Refiner):
        """Initialize for a given layout refinement object."""
        self._refiner = refiner
        self._segment_map = refiner.router.segment_map()
        self._wire_labels = self._make_wire_labels()

    def wire_labels(self) -> Iterator[WireLabel]:
        """Iterate over the labels for the wires."""
        yield from self._wire_labels

    def _make_wire_labels(self) -> Sequence[WireLabel]:
        """Create the labels for the connection wires."""
        labels: List[WireLabel] = []
        for wire in self._wires():
            label = self._make_wire_label(wire)
            if label:
                labels.append(label)
        return labels

    def _wires(self) -> Iterator[Wire]:
        """Return the wires in drawing order."""
        for net in self._refiner.networks():
            yield from net.wires()

    def _make_wire_label(self, wire: Wire) -> Optional[WireLabel]:
        """Create a label for a wire (if there should be one)."""
        attrs = wire.connection.attributes
        text = attrs.label
        if not text:
            return None
        all_spans: List[WireSegmentSpan] = []
        for seg in wire.segments():
            seg_spans = self._spans_for_label(seg)
            all_spans.extend(seg_spans)
        # Prefer segments with the segment orientation as the label.
        spans = [span for span in all_spans if span.follows_label()]
        # However, we will take any segment if we have to.
        if not spans:
            spans = all_spans
        # Pick the longest span-segment.
        spans.sort(key=len, reverse=True)
        span = spans[0]
        # Create the label object.
        return WireLabel(wire, span)

    def _spans_for_label(
            self, segment: WireSegment
    ) -> Iterator[WireSegmentSpan]:
        """Return the sub-segments on which the label can be placed."""
        min_coord, max_coord = segment.min_max_coordinates
        stops = [min_coord]
        cuts = self._refiner.segment_intersections(segment)
        stops.extend(cuts)
        stops.append(max_coord)
        for k, min_coord in enumerate(stops[:-1]):
            max_coord = stops[k + 1]
            span = WireSegmentSpan(segment, min_coord, max_coord)
            yield span
