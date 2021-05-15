"""Provides classes for declaring grid rows and columns."""

from typing import (
    Iterator,
    List,
)

from cassowary import Variable # type: ignore
from cassowary.expression import Constraint # type: ignore

from ..names import Named

from .connections import (
    DrawingWireSegment,
    DrawingWireStructure,
)

######################################################################

class Track(Named):
    """Contains the boxes and lines of a band."""

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
            name_prefix: str, coord_name: str,
    ):
        """Initialize the band at the given index."""
        name = f"{name_prefix}_{index}"
        super().__init__(name)
        self._index = index
        self._cmin = min_line
        self._cmax = max_line
        var_prefix = f"{name_prefix}_{index}_"
        var_name = f"{var_prefix}{coord_name}ref"
        self._cref = Variable(var_name)
        self._track = Track(name_prefix, index, coord_name)
        self._wire_structures: List[DrawingWireStructure] = []

    @property
    def index(self) -> int:
        """Index of the band in the grid."""
        return self._index

    @property
    def track(self) -> Track:
        """Track containing the contents of the band."""
        return self._track

    @property
    def cref(self) -> Variable:
        """Variable holding the reference coordinate along the axis."""
        return self._cref

    def add_structure(self, struct: DrawingWireStructure) -> None:
        """Associate a wire structure with the band."""
        self._wire_structures.append(struct)

    def constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the solver."""
        yield from self._line_constraints()
        yield from self._wire_constraints()
        yield from self._structure_constraints()

    def _line_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the lines."""
        track = self._track
        yield self._cmin <= track.cmin
        yield track.cmin <= self._cref
        yield self._cref <= track.cmax
        yield track.cmax <= self._cmax

    def _wire_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the connection wires."""
        # Segments must be inside the track of the band.
        track = self._track
        for seg in self._segments():
            yield seg.cmin >= track.cmin
            yield seg.cmax <= track.cmax

    def _segments(self) -> Iterator[DrawingWireSegment]:
        """Return the wire segments in the band."""
        for struct in self._wire_structures:
            for layer in struct:
                yield from layer

    def _structure_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the wire structures."""
        for struct in self._wire_structures:
            yield from struct.constraints()

    def optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the solver."""
        # Center connections on band axis.
        cref = self._cref
        for struct in self._wire_structures:
            layers = list(struct)
            first = layers[0]
            last = layers[-1]
            # Approach the reference line as much as possible.
            yield last.cref - cref == 0
            # Symmetry.
            yield last.cref - cref == cref - first.cref
