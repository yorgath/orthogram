"""Provides classes for declaring grid rows and columns."""

from typing import (
    Iterator,
    List,
)

from cassowary import Variable  # type: ignore
from cassowary.expression import Constraint  # type: ignore

from ..util import class_str

from .connections import (
    DrawingWireSegment,
    DrawingWireStructure,
)

######################################################################

class Band:
    """Row or column in the grid."""

    def __init__(
            self,
            index: int,
            name_prefix: str, coord_name: str,
    ):
        """Initialize the band with the given index number."""
        self._index = index
        self._name = name = f"{name_prefix}_{index}"
        var_prefix = f"{name}_{coord_name}"
        self._cmin = Variable(f"{var_prefix}min")
        self._cref = Variable(f"{var_prefix}ref")
        self._cmax = Variable(f"{var_prefix}max")
        self._wire_structures: List[DrawingWireStructure] = []

    def __repr__(self) -> str:
        """Represent as string."""
        content = repr(self._name)
        return class_str(self, content)

    @property
    def index(self) -> int:
        """Index number of the band in the grid."""
        return self._index

    @property
    def cmin(self) -> Variable:
        """Minimum coordinate perpendicular to the axis."""
        return self._cmin

    @property
    def cref(self) -> Variable:
        """Reference coordinate perpendicular to the axis."""
        return self._cref

    @property
    def cmax(self) -> Variable:
        """Maximum coordinate perpendicular to the axis."""
        return self._cmax

    def add_structure(self, struct: DrawingWireStructure) -> None:
        """Associate a wire structure with the band."""
        self._wire_structures.append(struct)

    def constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the solver."""
        yield from self._line_constraints()
        yield from self._wire_constraints()
        yield from self._structure_constraints()

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

    def _line_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the lines."""
        yield self._cmin <= self._cref
        yield self._cref <= self._cmax

    def _wire_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the connection wires."""
        # Segments must be inside the band.
        for seg in self._segments():
            yield seg.cmin >= self._cmin
            yield seg.cmax <= self._cmax

    def _structure_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the wire structures."""
        for struct in self._wire_structures:
            yield from struct.constraints()

    def _segments(self) -> Iterator[DrawingWireSegment]:
        """Iterate over the wire segments in the band."""
        for struct in self._wire_structures:
            for layer in struct:
                yield from layer
