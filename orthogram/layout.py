"""Lay out diagrams."""

from typing import (
    Iterable,
    Iterator,
    Optional,
)

from .diagram import Diagram

from .refine import (
    Connector,
    ConnectorSegment,
    Network,
    Refiner,
)

from .route import (
    AxisLocation,
    LayoutAxis,
    LayoutGrid,
    NodesAndPointsIterator,
    Router,
)

######################################################################

class Layout:
    """Layout of a diagram."""

    def __init__(self, diagram: Diagram):
        """Initialize the layout for the given diagram."""
        self._diagram = diagram
        # Calculate the coarse routes between the nodes.
        self._router = router = Router(diagram)
        # Refine the routes to calculate the exact connectors.
        self._refiner = Refiner(router)

    @property
    def diagram(self) -> Diagram:
        """The diagram for which this layout is built."""
        return self._diagram

    @property
    def grid(self) -> LayoutGrid:
        """Layout grid."""
        return self._router.grid
    
    def nodes_and_points(self) -> NodesAndPointsIterator:
        """Return an iterator over the nodes and their grid positions."""
        yield from self._router.nodes_and_points()

    def networks(self) -> Iterator[Network]:
        """Return an iterator over the calculated networks."""
        yield from self._refiner.networks()
