"""Lay out diagrams."""

from typing import Iterator

from .diagram import Diagram, DiagramDef, Node
from .geometry import Axis, IntPoint

from .refine import (
    Network,
    Refiner,
    Wire,
    WireSegment,
)

from .route import (
    LayoutGrid,
    NodesAndPointsIterator,
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

    def node_point(self, node: Node) -> IntPoint:
        """Return the position of the node in the grid."""
        return self._router.node_point(node)

    def networks(self) -> Iterator[Network]:
        """Return an iterator over the calculated networks."""
        yield from self._refiner.networks()
