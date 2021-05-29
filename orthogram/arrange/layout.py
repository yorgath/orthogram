"""Lay out diagrams."""

from typing import Iterator

from ..define import (
    Diagram,
    DiagramDef,
)

from .label import (
    WireLabel,
    Labeler,
)

from .net import (
    BundleStructure,
    Network,
)

from .refine import Refiner

from .route import (
    LayoutGrid,
    Router,
)

######################################################################

class Layout:
    """Layout of a diagram."""

    def __init__(self, diagram_def: DiagramDef):
        """Initialize the layout for the given diagram definition."""
        self._diagram = diagram = Diagram(diagram_def)
        # Calculate the coarse routes between the blocks.
        self._router = router = Router(diagram)
        # Refine the routes to calculate the exact wires.
        self._refiner = refiner = Refiner(router)
        # Arrange labels on the grid.
        self._labeler = Labeler(refiner)

    @property
    def diagram(self) -> Diagram:
        """The diagram for which this layout is built."""
        return self._diagram

    @property
    def grid(self) -> LayoutGrid:
        """Layout grid."""
        return self._router.grid

    def networks(self) -> Iterator[Network]:
        """Iterate over the calculated networks."""
        yield from self._refiner.networks()

    def bundle_structures(self) -> Iterator[BundleStructure]:
        """Iterate over the bundle structures."""
        yield from self._refiner.bundle_structures()

    def wire_labels(self) -> Iterator[WireLabel]:
        """Iterate over the wire labels."""
        yield from self._labeler.wire_labels()
