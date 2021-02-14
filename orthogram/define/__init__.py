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

from .diagram import (
    Block,
    Connection,
    Diagram,
    DiagramDef,
    Node,
)
