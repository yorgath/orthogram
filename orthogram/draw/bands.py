"""Provides classes for declaring grid rows and columns."""

from typing import (
    Dict,
    Iterator,
    Sequence,
)

from cassowary import Variable # type: ignore
from cassowary.expression import Constraint # type: ignore

from .connections import Lane
from .names import Named

######################################################################

class Track(Named):
    """Contains the boxes and lanes of a band."""

    def __init__(self, name_prefix: str, index: int, coord_name: str):
        """Initialize an empty track."""
        name = f"{name_prefix}_{index}_track"
        super().__init__(name)
        var_prefix = f"{name}_{coord_name}"
        var_name = f"{var_prefix}min"
        self._cmin = Variable(var_name)
        var_name = f"{var_prefix}max"
        self._cmax = Variable(var_name)

    @property
    def cmin(self) -> Variable:
        """Variable holding the minimum coordinate along the axis."""
        return self._cmin

    @property
    def cmax(self) -> Variable:
        """Variable holding the maximum coordinate along the axis."""
        return self._cmax

######################################################################

class Band(Named):
    """Row or column in the grid."""

    def __init__(
            self,
            index: int,
            min_line: Variable, max_line: Variable,
            lane_distance: float,
            name_prefix: str, coord_name: str,
    ):
        """Initialize the band at the given index."""
        name = f"{name_prefix}_{index}"
        super().__init__(name)
        self._index = index
        self._cmin = min_line
        self._cmax = max_line
        self._lane_distance = lane_distance
        self._lanes_by_offset: Dict[int, Lane] = {}
        var_prefix = f"{name_prefix}_{index}_"
        var_name = f"{var_prefix}{coord_name}ref"
        self._cref = Variable(var_name)
        self._track = Track(name_prefix, index, coord_name)

    @property
    def index(self) -> int:
        """Index of the band in the grid."""
        return self._index

    @property
    def track(self) -> Track:
        """Track containing the contents of the band."""
        return self._track

    def lane(self, offset: int) -> Lane:
        """Return the lane at the given offset."""
        return self._get_or_create_lane(offset)

    def _get_or_create_lane(self, offset: int) -> Lane:
        """Return the lane at the given offset.

        It will create a new lane if necessary.

        """
        lanes = self._lanes_by_offset
        lane = lanes.get(offset)
        if not lane:
            lane = Lane(self._name, self._index, offset)
            lanes[offset] = lane
        return lane

    def lane_ref(self, offset: int) -> Variable:
        """Reference line of the lane at the given offset.

        If there is no lane at the offset (which actually happens if
        the track is empty), it returns the reference line of the band
        itself.

        """
        lane = self._lanes_by_offset.get(offset)
        if lane:
            return lane.cref
        return self._cref

    def lanes_with_end_at(self, coord: int) -> Iterator[Lane]:
        """Return the lanes with a segment ending at the coordinate."""
        for lane in self._lanes():
            if lane.has_wire_end_at(coord):
                yield lane

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the solver."""
        yield from self._line_constraints()
        yield from self._lane_constraints()

    def _line_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the lines."""
        track = self._track
        yield self._cmin <= track.cmin
        yield track.cmin <= self._cref
        yield self._cref <= track.cmax
        yield track.cmax <= self._cmax

    @property
    def cmin(self) -> Variable:
        """Variable holding the minimum coordinate along the axis."""
        return self._cmin

    @property
    def cref(self) -> Variable:
        """Variable holding the reference coordinate along the axis."""
        return self._cref

    @property
    def cmax(self) -> Variable:
        """Variable holding the maximum coordinate along the axis."""
        return self._cmax

    def _lane_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the lanes."""
        dist = self._lane_distance
        lanes = list(self._lanes())
        # Place lanes relative to the reference line.
        cref = self._cref
        draw_offset = self._lane_draw_offset()
        for lane in lanes:
            draw_offset += dist + lane.width_before
            yield lane.cref == cref + draw_offset
            draw_offset += lane.width_after
            yield from lane.constraints()
        # Lanes must be inside the track of the band.
        if lanes:
            track = self._track
            yield track.cmin <= lanes[0].cmin
            yield track.cmax >= lanes[-1].cmax

    def _lane_draw_offset(self) -> float:
        """Relative coordinate to start drawing lanes from."""
        width = 0.0
        dist = self._lane_distance
        lanes = self._lanes()
        n_lanes = len(lanes)
        for i, lane in enumerate(lanes):
            width += dist + lane.total_width
            if i == 0:
                width -= lane.margin_before
            if i == n_lanes - 1:
                width += dist
                width -= lane.margin_after
        result = -0.5 * width
        if n_lanes:
            result -= lanes[0].margin_before
        return result

    def _lanes(self) -> Sequence[Lane]:
        """Return the lanes ordered by offset."""
        result = []
        by_offset = self._lanes_by_offset
        offsets = sorted(by_offset)
        for offset in offsets:
            lane = by_offset[offset]
            result.append(lane)
        return result
