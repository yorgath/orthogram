"""Draw a diagram layout as an image file."""

from datetime import datetime
from enum import Enum, auto
from typing import Iterator

import math

from cairo import (
    Context,
    ImageSurface,
)

from cassowary import (  # type: ignore
    SimplexSolver,
    REQUIRED,
    WEAK,
)

from cassowary.expression import Constraint # type: ignore

from shapely.geometry import LineString # type: ignore

from ..arrange import Layout

from ..define import (
    AreaAttributes,
    ConnectionAttributes,
    DiagramAttributes,
    LineAttributes,
)

from ..util import log_debug

from .blocks import BlockBox

from .connections import (
    DrawingNetwork,
    DrawingWire,
    DrawingWireSegment,
)

from .containers import Container

from .functions import (
    line_area_attributes,
    line_buffer_attributes,
    new_surface,
)

from .grid import DrawingGrid
from .labels import Label
from .shapes import Arrow, WireLine

######################################################################

class _Anchor(Enum):
    """Text anchor."""

    START = auto()
    MIDDLE = auto()
    END = auto()

######################################################################

class Drawing(Container):
    """Drawing of a diagram layout."""

    def __init__(self, layout: Layout):
        """Initialize the drawing of a layout."""
        time_start = datetime.now()
        self._layout = layout
        # Diagram label.
        dia = layout.diagram
        attrs = dia.attributes
        ori = dia.label_orientation
        label = Label(attrs, attrs, ori)
        super().__init__("drawing", label)
        # Create the grid that contains the elements of the drawing.
        self._grid = DrawingGrid(self._layout)
        # The coordinates of the elements are calculated by creating
        # constraints between the elements and then solving these
        # constraints.
        self._solver = SimplexSolver()
        self._configure_variables()
        self._add_constraints()
        elapsed = datetime.now() - time_start
        # DEBUG: Uncomment the following line to print the time needed
        # to calculate the drawing.  Development only!
        # log_debug(f"Initialized drawing in {elapsed}")

    def _configure_variables(self) -> None:
        """Configure some of the constraint solver variables."""
        solver = self._solver
        # Shape coordinates are calculated relative to the start of
        # the drawing.  Fix the top left corner at zero and calculate
        # from there.
        xmin = self._xmin
        xmin.value = 0.0
        solver.add_stay(xmin, strength=REQUIRED)
        ymin = self._ymin
        ymin.value = 0.0
        solver.add_stay(ymin, strength=REQUIRED)

    def _add_constraints(self) -> None:
        """Add the constraints to the solver."""
        add_constraint = self._solver.add_constraint
        for constraint in self._required_constraints():
            add_constraint(constraint, strength=REQUIRED)
        for constraint in self._optional_constraints():
            add_constraint(constraint, strength=WEAK)

    def _required_constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the solver."""
        yield from self._grid.constraints()
        yield from self._own_required_constraints()

    def _optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the solver."""
        yield from self._grid.optional_constraints()
        yield from self._own_optional_constraints()

    def _own_required_constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the drawing itself."""
        # Satisfy minimum requested dimensions.
        attrs = self._attributes()
        yield self._xmax >= self._xmin + attrs.min_width
        yield self._ymax >= self._ymin + attrs.min_height
        # Grid must be inside drawing.
        grid = self._grid
        top = self.padding_top
        bot = self.padding_bottom
        lef = self.padding_left
        rig = self.padding_right
        yield grid.xmin >= self._xmin + lef
        yield grid.xmax <= self._xmax - rig
        yield grid.ymin >= self._ymin + top
        yield grid.ymax <= self._ymax - bot

    def _own_optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the drawing itself."""
        grid = self._grid
        # Minimize grid.
        yield grid.xmax == grid.xmin
        yield grid.ymax == grid.ymin
        # Center grid on drawing.
        top = self.padding_top
        bot = self.padding_bottom
        lef = self.padding_left
        rig = self.padding_right
        yield grid.xmin - self._xmin - lef == self._xmax - grid.xmax - rig
        yield grid.ymin - self._ymin - top == self._ymax - grid.ymax - bot

    def write_png(self, filename: str) -> None:
        """Write the drawing to a PNG file."""
        attrs = self._attributes()
        width = self._xmax.value
        height = self._ymax.value
        with new_surface(attrs, width, height) as surface:
            color = attrs.fill
            if color:
                ctx = Context(surface)
                ctx.set_source_rgba(*color.rgba)
                ctx.rectangle(0, 0, width, height)
                ctx.fill()
            self._draw_blocks(surface)
            self._draw_connections(surface)
            self._draw_block_labels(surface)
            self._draw_connection_labels(surface)
            self._draw_diagram_label(surface)
            # DEBUG: Uncomment this to visualize the grid.
            # self._draw_grid(surface)
            with open(filename, "wb") as file:
                surface.write_to_png(file)

    def _draw_diagram_box(self, surface: ImageSurface) -> None:
        """Draw the box around the diagram."""
        self._draw_container(surface, self)

    def _draw_blocks(self, surface: ImageSurface) -> None:
        """Draw the diagram blocks."""
        for box in self._block_boxes():
            self._draw_container(surface, box)

    def _draw_container(self, surface: ImageSurface, box: Container) -> None:
        """Draw the box of a container."""
        ctx = Context(surface)
        x_start = box.xmin.value
        y_start = box.ymin.value
        width = box.xmax.value - x_start
        height = box.ymax.value - y_start
        attrs = box.attributes
        # Draw the interior first.
        is_visible = self._configure_context_for_fill(ctx, attrs)
        if is_visible:
            ctx.rectangle(x_start, y_start, width, height)
            ctx.fill()
        # Draw borders *inside* the box.
        line_width = attrs.stroke_width
        x_start += line_width / 2
        y_start += line_width / 2
        width -= line_width
        height -= line_width
        ctx.rectangle(x_start, y_start, width, height)
        is_visible = self._configure_context_for_line(ctx, attrs)
        if is_visible:
            ctx.stroke()

    def _draw_block_labels(self, surface: ImageSurface) -> None:
        """Draw the labels of the blocks."""
        for box in self._block_boxes():
            self._draw_container_label(surface, box)

    def _draw_connections(self, surface: ImageSurface) -> None:
        """Draw the connections."""
        for net in self._networks():
            # Collect the lines necessary for the drawing.
            lines = []
            for wire in net.wires():
                line = self._wire_line(wire)
                lines.append(line)
            # Draw the background of the network to cover the other
            # lines drawn under it.
            for line in lines:
                self._draw_wire_buffer(surface, line)
            # Draw the actual lines.
            for line in lines:
                # Draw the line.
                self._draw_wire_line(surface, line)
                # Draw the arrows.
                attrs = line.connection_attributes
                arrows = [line.start_arrow, line.end_arrow]
                for arrow in arrows:
                    if arrow:
                        self._draw_arrow(surface, arrow, attrs)

    def _wire_line(self, wire: DrawingWire) -> WireLine:
        """Create a line between the two ends of the wire."""
        line = wire.line_string
        grid = self._grid
        lwire = wire.layout_wire
        connection = lwire.connection
        box1 = grid.block_box(connection.start.block)
        box2 = grid.block_box(connection.end.block)
        return WireLine(lwire, box1.polygon, box2.polygon, line)

    @classmethod
    def _draw_wire_buffer(cls, surface: ImageSurface, line: WireLine) -> None:
        """Draw the buffer of the wire."""
        attrs = line_buffer_attributes(line.connection_attributes)
        line = line.wire_line_string
        cls._draw_line(surface, line, attrs)

    @classmethod
    def _draw_wire_line(cls, surface: ImageSurface, line: WireLine) -> None:
        """Draw the line of the wire."""
        attrs = line.connection_attributes
        line = line.wire_line_string
        cls._draw_line(surface, line, attrs)

    @classmethod
    def _draw_line(
            cls,
            surface: ImageSurface,
            line: LineString,
            attrs: LineAttributes,
    ) -> None:
        """Draw a line inside the given context."""
        ctx = Context(surface)
        is_visible = cls._configure_context_for_line(ctx, attrs)
        if not is_visible:
            return
        for i, xy_pair in enumerate(line.coords):
            if i == 0:
                ctx.move_to(*xy_pair)
            else:
                ctx.line_to(*xy_pair)
        ctx.stroke()

    @classmethod
    def _draw_arrow(
            cls,
            surface: ImageSurface,
            arrow: Arrow,
            attrs: ConnectionAttributes,
    ) -> None:
        """Draw the arrow on the surface with the given attributes."""
        geom = arrow.geometry
        if not geom:
            return
        area_attrs = line_area_attributes(attrs)
        ctx = Context(surface)
        is_visible = cls._configure_context_for_fill(ctx, area_attrs)
        if not is_visible:
            return
        for i, xy_pair in enumerate(geom.coords):
            if i == 0:
                ctx.move_to(*xy_pair)
            else:
                ctx.line_to(*xy_pair)
        ctx.fill()

    def _draw_diagram_label(self, surface: ImageSurface) -> None:
        """Draw the label of the diagram."""
        self._draw_container_label(surface, self)

    @classmethod
    def _draw_container_label(
            cls,
            surface: ImageSurface,
            box: Container,
    ) -> None:
        """Draw the label of a container box."""
        label = box.label
        if not label:
            return
        x_box = box.xmin.value
        y_box = box.ymin.value
        width = box.xmax.value - x_box
        height = box.ymax.value - y_box
        attrs = box.attributes
        pos = attrs.label_position
        border = attrs.stroke_width
        label_height = label.height
        label_distance = attrs.label_distance
        dist = border + label_distance + label_height / 2.0
        if pos.is_left():
            anchor = _Anchor.START
            x_label = x_box + border + label_distance
        elif pos.is_right():
            anchor = _Anchor.END
            x_label = x_box + width - border - label_distance
        else:
            anchor = _Anchor.MIDDLE
            x_label = x_box + width / 2.0
        if pos.is_top():
            y_label = y_box + dist
        elif pos.is_bottom():
            y_label = y_box + height - dist
        else:
            y_label = y_box + height / 2.0
        cls._draw_label(surface, label, x_label, y_label, anchor)

    def _draw_connection_labels(self, surface: ImageSurface) -> None:
        """Draw the labels of the connections."""
        for seg in self._wire_segments():
            self._draw_segment_label(surface, seg)

    def _draw_segment_label(
            self,
            surface: ImageSurface,
            segment: DrawingWireSegment,
    ) -> None:
        """Draw the label of a wire segment."""
        label = segment.label
        if not label:
            return
        if segment.is_horizontal():
            x_start = label.cmin.value
            x_end = label.cmax.value
            y_start = segment.start.y.value
            y_end = segment.end.y.value
        else:
            y_start = label.cmin.value
            y_end = label.cmax.value
            x_start = segment.start.x.value
            x_end = segment.end.x.value
        x_label = 0.5 * (x_start + x_end)
        y_label = 0.5 * (y_start + y_end)
        disp = segment.label_displacement
        x_label += disp[0]
        y_label += disp[1]
        self._draw_label(
            surface, label.drawing_label,
            x_label, y_label, _Anchor.MIDDLE
        )

    @classmethod
    def _draw_label(
            cls,
            surface: ImageSurface,
            label: Label,
            x_center: float, y_center: float,
            anchor: _Anchor,
    ) -> None:
        """Draw the label at the given point."""
        lines = list(label.lines())
        if not lines:
            return
        ctx = label.new_context(surface)
        x_step = 0.0
        y_step = label.height / len(lines)
        if label.is_vertical():
            ctx.translate(x_center, y_center)
            ctx.rotate(-0.5 * math.pi)
            ctx.translate(-x_center, -y_center)
        x_line = x_center
        y_line = y_center - 0.5 * (len(lines) - 1.5) * y_step
        for text in lines:
            ctx.move_to(x_line, y_line)
            extents = ctx.text_extents(text)
            if anchor is _Anchor.END:
                ctx.rel_move_to(-extents.width, 0)
            elif anchor is _Anchor.MIDDLE:
                ctx.rel_move_to(-0.5 * extents.width, 0)
            ctx.show_text(text)
            x_line += x_step
            y_line += y_step

    @staticmethod
    def _configure_context_for_line(
            ctx: Context,
            attrs: LineAttributes,
    ) -> bool:
        """Prepare the context for line drawing.

        Returns True if drawing will be visible.

        """
        color = attrs.stroke
        if not color:
            return False
        width = attrs.stroke_width
        if not width:
            return False
        ctx.set_source_rgba(*color.rgba)
        ctx.set_line_width(width)
        dashes = attrs.stroke_dasharray
        if dashes:
            ctx.set_dash(dashes)
        return True

    @staticmethod
    def _configure_context_for_fill(
            ctx: Context,
            attrs: AreaAttributes,
    ) -> bool:
        """Prepare the context for filling an area.

        Returns True if drawing will be visible.

        """
        color = attrs.fill
        if not color:
            return False
        ctx.set_source_rgba(*color.rgba)
        return True

    def _attributes(self) -> DiagramAttributes:
        """Attributes of the diagram."""
        return self._layout.diagram.attributes

    def _block_boxes(self) -> Iterator[BlockBox]:
        """Return the boxes of the diagram blocks."""
        yield from self._grid.block_boxes()

    def _wire_segments(self) -> Iterator[DrawingWireSegment]:
        """Return the segments of all the wires."""
        for wire in self._wires():
            yield from wire.segments()

    def _wires(self) -> Iterator[DrawingWire]:
        """Return the wires."""
        for net in self._networks():
            yield from net.wires()

    def _networks(self) -> Iterator[DrawingNetwork]:
        """Return the networks of drawing wires."""
        yield from self._grid.networks()

    def _draw_grid(self, surface: ImageSurface) -> None:
        """Draw the outline of the grid."""
        xmin = self._xmin.value
        xmax = self._xmax.value
        ymin = self._ymin.value
        ymax = self._ymax.value
        grid = self._grid
        ctx = Context(surface)
        ctx.set_line_width(1.0)
        grade = 0.5
        # Sides of rows and columns.
        ctx.set_source_rgb(grade, grade, 1.0)
        for hline in grid.horizontal_lines():
            line_y = hline.value
            ctx.move_to(xmin, line_y)
            ctx.line_to(xmax, line_y)
            ctx.stroke()
        for vline in grid.vertical_lines():
            line_x = vline.value
            ctx.move_to(line_x, ymin)
            ctx.line_to(line_x, ymax)
            ctx.stroke()
        # Tracks.
        ctx.set_source_rgb(grade, 1.0, grade)
        ctx.set_dash([4, 2])
        for row in grid.rows():
            track = row.track
            variables = [track.cmin, track.cmax]
            for var in variables:
                line_y = var.value
                ctx.move_to(xmin, line_y)
                ctx.line_to(xmax, line_y)
                ctx.stroke()
        for col in grid.columns():
            track = col.track
            variables = [track.cmin, track.cmax]
            for var in variables:
                line_x = var.value
                ctx.move_to(line_x, ymin)
                ctx.line_to(line_x, ymax)
                ctx.stroke()
        # Reference lines of the rows and columns.
        ctx.set_source_rgb(1.0, grade, grade)
        ctx.set_dash([2, 4])
        for row in grid.rows():
            line_y = row.cref.value
            ctx.move_to(xmin, line_y)
            ctx.line_to(xmax, line_y)
            ctx.stroke()
        for col in grid.columns():
            line_x = col.cref.value
            ctx.move_to(line_x, ymin)
            ctx.line_to(line_x, ymax)
            ctx.stroke()
