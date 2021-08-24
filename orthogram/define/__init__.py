"""Provides classes to build diagrams with."""

from .attributes import (
    AreaAttributes,
    AttributeMap,
    BlockAttributes,
    Color,
    ConnectionAttributes,
    ContainerAttributes,
    DiagramAttributes,
    FontStyle,
    FontWeight,
    LabelPosition,
    LineAttributes,
    Side,
    TextAttributes,
    TextOrientation,
)

from .build import Builder

from .defs import (
    ConnectionDef,
    DiagramDef,
    LabelDef,
    RowDef,
    UserBlockDef,
)

from .load import Loader

from .diagram import (
    Block,
    Connection,
    ConnectionLabelPosition,
    Diagram,
    Label,
    Node,
)
