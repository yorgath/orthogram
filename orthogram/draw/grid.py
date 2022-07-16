"""Provides classes for creating a drawing grid."""

from collections import OrderedDict

from typing import (
    Callable,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Sequence,
    Tuple,
)

from cassowary import Variable  # type: ignore
from cassowary.expression import Constraint  # type: ignore

from ..arrange import (
    Joint,
    Layout,
    RouteSegment,
    Wire,
    WireSegment,
)

from ..define import (
    Block,
    ConnectionLabelPosition,
)

from ..geometry import (
    Axis,
    IntPoint,
)

from ..util import (
    class_str,
    grid_str,
)

from .bands import Band
from .blocks import DrawingBlock

from .connections import (
    DrawingJoint,
    DrawingNetwork,
    DrawingWire,
    DrawingWireLayer,
    DrawingWireSegment,
    DrawingWireStructure,
)

from .labels import (
    DrawingWireEndLabel,
    DrawingWireLabel,
    DrawingWireMiddleLabel,
)

######################################################################

class DrawingCell:
    """Cell in the drawing grid."""

    def __init__(self, point: IntPoint) -> None:
        """Initialize an empty cell."""
        self._point = point
        self._blocks_top: List[DrawingBlock] = []
        self._blocks_bottom: List[DrawingBlock] = []
        self._blocks_left: List[DrawingBlock] = []
        self._blocks_right: List[DrawingBlock] = []

    def __repr__(self) -> str:
        """Represent as string."""
        point = self._point
        i = point.i
        j = point.j
        content = f"i={i}, j={j}"
        return class_str(self, content)

    def blocks_top(self) -> Iterator[DrawingBlock]:
        """Iterate over the blocks at the top side of the cell."""
        yield from self._blocks_top

    def blocks_bottom(self) -> Iterator[DrawingBlock]:
        """Iterate over the blocks at the bottom side of the cell."""
        yield from self._blocks_bottom

    def blocks_left(self) -> Iterator[DrawingBlock]:
        """Iterate over the blocks at the left side of the cell."""
        yield from self._blocks_left

    def blocks_right(self) -> Iterator[DrawingBlock]:
        """Iterate over the blocks at the right side of the cell."""
        yield from self._blocks_right

    def place_block_top(self, block: DrawingBlock) -> None:
        """Place a block at the top side of the cell."""
        self._blocks_top.append(block)

    def place_block_bottom(self, block: DrawingBlock) -> None:
        """Place a block at the bottom side of the cell."""
        self._blocks_bottom.append(block)

    def place_block_left(self, block: DrawingBlock) -> None:
        """Place a block at the left side of the cell."""
        self._blocks_left.append(block)

    def place_block_right(self, block: DrawingBlock) -> None:
        """Place a block at the right side of the cell."""
        self._blocks_right.append(block)

######################################################################

class DrawingGrid:
    """Grid of the drawing."""

    def __init__(self, layout: Layout):
        """Initialize for a diagram layout."""
        self._layout = layout
        self._rows = self._make_rows()
        self._columns = self._make_columns()
        self._cell_rows = self._make_cells()
        self._blocks = self._make_blocks()
        self._block_map = self._make_block_map()
        self._joint_map = self._make_joint_map()
        self._networks = self._make_drawing_networks()
        self._wire_segment_map = self._make_wire_segment_map()
        self._route_segment_map = self._make_route_segment_map()
        self._axis_structures = self._make_axis_structures()
        self._apply_band_variables()
        self._apply_layer_variables()
        self._add_labels_to_wires()
        self._place_structures()
        self._connect_blocks()

    def __repr__(self) -> str:
        """Represent as string."""
        height = len(self._rows)
        width = len(self._columns)
        content = grid_str(height, width)
        return class_str(self, content)

    def rows(self) -> Iterator[Band]:
        """Iterate over the rows top to bottom."""
        yield from self._rows

    def columns(self) -> Iterator[Band]:
        """Iterate over the columns left to right."""
        yield from self._columns

    @property
    def xmin(self) -> Variable:
        """Minimum coordinate along the X axis."""
        return self._columns[0].cmin

    @property
    def xmax(self) -> Variable:
        """Maximum coordinate along the X axis."""
        return self._columns[-1].cmax

    @property
    def ymin(self) -> Variable:
        """Minimum coordinate along the Y axis."""
        return self._rows[0].cmin

    @property
    def ymax(self) -> Variable:
        """Maximum coordinate along the Y axis."""
        return self._rows[-1].cmax

    def blocks(self) -> Iterator[DrawingBlock]:
        """Iterate over the drawing blocks."""
        yield from self._blocks

    def block(self, diagram_block: Block) -> DrawingBlock:
        """Return the drawing block of the given diagram block."""
        return self._block_map[diagram_block]

    def networks(self) -> Iterator[DrawingNetwork]:
        """Iterate over the networks of drawing wires."""
        yield from self._networks

    def constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the solver."""
        yield from self._block_constraints()
        yield from self._wire_constraints()
        yield from self._band_constraints()
        yield from self._padding_constraints()

    def optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the solver."""
        yield from self._block_optional_constraints()
        yield from self._band_optional_constraints()

    def _make_rows(self) -> Sequence[Band]:
        """Create the rows."""
        n_rows = self._layout.grid.height
        return self._make_bands(n_rows, "row", "y")

    def _make_columns(self) -> Sequence[Band]:
        """Create the columns."""
        n_cols = self._layout.grid.width
        return self._make_bands(n_cols, "col", "x")

    @staticmethod
    def _make_bands(
            n_bands: int,
            name_prefix: str, coord_name: str,
    ) -> Sequence[Band]:
        """Create rows or columns."""
        bands: List[Band] = []
        for i in range(n_bands):
            band = Band(i, name_prefix, coord_name)
            bands.append(band)
        return bands

    def _make_cells(self) -> Sequence[Sequence[DrawingCell]]:
        """Create the cells."""
        rows = []
        height = len(self._rows)
        width = len(self._columns)
        for i in range(height):
            row = []
            for j in range(width):
                point = IntPoint(i, j)
                cell = DrawingCell(point)
                row.append(cell)
            rows.append(row)
        return rows

    def _make_blocks(self) -> Sequence[DrawingBlock]:
        """Create drawing blocks for the diagram blocks.

        The sequence of the blocks in the drawing is the same as the
        sequence of the corresponding blocks in the diagram.

        """
        draw_blocks = []
        layout = self._layout
        dia = layout.diagram
        dia_attrs = dia.attributes
        lgrid = layout.grid
        rows = self._rows
        cols = self._columns
        for dia_block in dia.blocks():
            bounds = lgrid.block_bounds(dia_block)
            # It is possible that some blocks declared in the DDF are
            # not placed in the layout.
            if not bounds:
                continue
            top = rows[bounds.imin]
            bottom = rows[bounds.imax]
            left = cols[bounds.jmin]
            right = cols[bounds.jmax]
            draw_block = DrawingBlock(
                dia_block,
                dia_attrs,
                top, bottom, left, right,
            )
            self._associate_block_with_cells(draw_block)
            draw_blocks.append(draw_block)
        return draw_blocks

    def _associate_block_with_cells(self, block: DrawingBlock) -> None:
        """Associate the block with the grid cells under it."""
        cells = self._cell_rows
        jmin = block.left_column.index
        jmax = block.right_column.index
        i = block.top_row.index
        for j in range(jmin, jmax + 1):
            cells[i][j].place_block_top(block)
        i = block.bottom_row.index
        for j in range(jmin, jmax + 1):
            cells[i][j].place_block_bottom(block)
        imin = block.top_row.index
        imax = block.bottom_row.index
        j = block.left_column.index
        for i in range(imin, imax + 1):
            cells[i][j].place_block_left(block)
        j = block.right_column.index
        for i in range(imin, imax + 1):
            cells[i][j].place_block_right(block)

    def _make_block_map(self) -> Mapping[Block, DrawingBlock]:
        """Map each diagram block to its corresponding block in the drawing."""
        result = OrderedDict()
        for draw_block in self._blocks:
            result[draw_block.diagram_block] = draw_block
        return result

    def _make_joint_map(self) -> Mapping[Joint, DrawingJoint]:
        """Map each layout joint to a drawing joint."""
        result: MutableMapping[Joint, DrawingJoint] = OrderedDict()
        for net in self._layout.networks():
            for wire in net.wires():
                for seg in wire:
                    for ljoint in seg.joints:
                        if ljoint not in result:
                            result[ljoint] = DrawingJoint(ljoint)
        return result

    def _layout_wire_segments(self) -> Iterator[WireSegment]:
        """Return the connection wire segments of the layout."""
        for wire in self._layout_wires():
            yield from wire

    def _layout_wires(self) -> Iterator[Wire]:
        """Return the connection wires of the layout."""
        for net in self._layout.networks():
            yield from net.wires()

    def _make_drawing_networks(self) -> Sequence[DrawingNetwork]:
        """Create drawing wire networks out of the layout networks."""
        result = []
        for lnet in self._layout.networks():
            dnet = DrawingNetwork(lnet.name)
            for lwire in lnet.wires():
                dwire = self._make_drawing_wire(lwire)
                dnet.append(dwire)
            result.append(dnet)
        return result

    def _make_drawing_wire(self, layout_wire: Wire) -> DrawingWire:
        """Create a drawing wire out of a layout wire."""
        dwire = DrawingWire(layout_wire)
        # Populate the wire with segments.
        jmap = self._joint_map
        dist = self._layout.diagram.attributes.connection_distance
        size = len(layout_wire)
        for i, lseg in enumerate(layout_wire):
            is_first = bool(i == 0)
            is_last = bool(i == size - 1)
            start = jmap[lseg.start]
            end = jmap[lseg.end]
            dseg = DrawingWireSegment(
                layout_segment=lseg,
                connection_distance=dist,
                start=start, end=end,
                is_first=is_first, is_last=is_last,
            )
            dwire.append(dseg)
        return dwire

    def _make_wire_segment_map(self) -> Mapping[WireSegment,
                                                DrawingWireSegment]:
        """Map layout wire segments to drawing wire segments."""
        result: MutableMapping[WireSegment, DrawingWireSegment] = OrderedDict()
        for dseg in self._wire_segments():
            result[dseg.layout_segment] = dseg
        return result

    def _make_route_segment_map(self) -> Mapping[RouteSegment,
                                                 DrawingWireSegment]:
        """Map layout route segments to drawing wire segments."""
        result: MutableMapping[RouteSegment, DrawingWireSegment] = OrderedDict()
        for wseg, dseg in self._wire_segment_map.items():
            result[wseg.route_segment] = dseg
        return result

    def _make_axis_structures(
            self
    ) -> Mapping[Axis, Collection[DrawingWireStructure]]:
        """Create drawing wire structures out of layout bundle structures.

        The result is a map from grid axes to the structures that lie
        on them.

        """
        result: Dict[Axis, List[DrawingWireStructure]] = OrderedDict()
        layout = self._layout
        dist = layout.diagram.attributes.connection_distance
        segmap = self._route_segment_map
        for bstruct in layout.bundle_structures():
            axis = bstruct.axis
            dstructs = result.get(axis)
            if not dstructs:
                result[axis] = dstructs = []
            struct_name = bstruct.name
            dstruct = DrawingWireStructure(struct_name, axis, dist)
            for blayer in bstruct:
                dlayer = DrawingWireLayer(struct_name, blayer.offset)
                for net_bundle in blayer:
                    for rseg in net_bundle.bundle.route_segments():
                        dseg = segmap[rseg]
                        dlayer.append(dseg)
                dstruct.add(dlayer)
            dstructs.append(dstruct)
        return result

    def _apply_band_variables(self) -> None:
        """Use row and column reference lines for joint coordinates."""
        rows = self._rows
        cols = self._columns
        for wire in self._wires():
            segments = list(wire)
            first_seg = segments[0]
            last_seg = segments[-1]
            seg_joints = [
                (first_seg, first_seg.start),
                (last_seg, last_seg.end),
            ]
            for seg, joint in seg_joints:
                point = joint.layout_joint.point
                if seg.grid_vector.is_horizontal():
                    col = cols[point.j]
                    joint.x = col.cref
                else:
                    row = rows[point.i]
                    joint.y = row.cref

    def _apply_layer_variables(self) -> None:
        """Use layer variables in segments."""
        for struct in self._structures():
            for layer in struct:
                cref = layer.cref
                for seg in layer:
                    seg.cref = cref

    def _add_labels_to_wires(self) -> None:
        """Add the labels to the wires that have ones."""
        layout = self._layout
        dia_attrs = layout.diagram.attributes
        rows = self._rows
        cols = self._columns
        draw_segments = self._wire_segment_map
        for lay_label in layout.wire_labels():
            lay_segment = lay_label.segment
            lay_min, lay_max = lay_label.grid_vector.min_max_coordinates
            draw_segment = draw_segments[lay_segment]
            if draw_segment.grid_vector.is_horizontal():
                side_bands = cols
            else:
                side_bands = rows
            cmin = side_bands[lay_min].cmax
            cmax = side_bands[lay_max].cmin
            wire_label: DrawingWireLabel
            if lay_label.position is ConnectionLabelPosition.MIDDLE:
                wire_label = DrawingWireMiddleLabel(
                    lay_label, dia_attrs, cmin, cmax)
            else:
                wire_label = DrawingWireEndLabel(lay_label, dia_attrs)
            draw_segment.add_label(wire_label)

    def _place_structures(self) -> None:
        """Associate wire structures with bands.

        The structures are used to center the connections on the grid
        lines.

        """
        rows = self._rows
        cols = self._columns
        for struct in self._structures():
            axis = struct.axis
            index = axis.coordinate
            if axis.is_horizontal():
                bands = rows
            else:
                bands = cols
            band = bands[index]
            band.add_structure(struct)

    def _structures(self) -> Iterator[DrawingWireStructure]:
        """Iterate over the wire structures."""
        for structs in self._axis_structures.values():
            yield from structs

    def _connect_blocks(self) -> None:
        """Connect the blocks and the wire segments."""
        block_map = self._block_map
        seg_map = self._wire_segment_map
        for lwire in self._layout_wires():
            sides = lwire.attachment_sides()
            conn = lwire.connection
            dia_block_lsegs = [
                (conn.start.block, lwire[0], sides[0], True),
                (conn.end.block, lwire[-1], sides[-1], False),
            ]
            for dia_block, lseg, side, out in dia_block_lsegs:
                draw_block = block_map[dia_block]
                dseg = seg_map[lseg]
                draw_block.attach_segment(dseg, side, out)

    def _block_constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the blocks."""
        for block in self._blocks:
            yield from block.constraints()

    def _block_optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the blocks."""
        for block in self._blocks:
            yield from block.optional_constraints()

    def _wire_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the connection wires."""
        for seg in self._wire_segments():
            yield from seg.constraints()

    def _band_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for the rows and columns."""
        band_seqs = [
            self._rows,
            self._columns,
        ]
        for band_seq in band_seqs:
            previous = None
            for current in band_seq:
                yield from current.constraints()
                if previous:
                    yield current.cmin >= previous.cmax
                previous = current

    def _band_optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the rows and columns."""
        for band in self._bands():
            yield from band.optional_constraints()

    def _bands(self) -> Iterator[Band]:
        """Return the rows and the columns."""
        yield from self._rows
        yield from self._columns

    def _padding_constraints(self) -> Iterator[Constraint]:
        """Generate the constraints for padding overlapping blocks."""
        yield from self._padding_top_constraints()
        yield from self._padding_bottom_constraints()
        yield from self._padding_left_constraints()
        yield from self._padding_right_constraints()

    def _padding_top_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for padding one block over another."""
        pairs = self._block_pairs(DrawingCell.blocks_top)
        for block_under, block_over in pairs:
            pad = block_under.box.padding_top
            yield block_under.box.ymin <= block_over.box.ymin - pad

    def _padding_bottom_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for padding one block under another."""
        pairs = self._block_pairs(DrawingCell.blocks_bottom)
        for block_under, block_over in pairs:
            pad = block_under.box.padding_bottom
            yield block_under.box.ymax >= block_over.box.ymax + pad

    def _padding_left_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for padding one block left of another."""
        pairs = self._block_pairs(DrawingCell.blocks_left)
        for block_under, block_over in pairs:
            pad = block_under.box.padding_left
            yield block_under.box.xmin <= block_over.box.xmin - pad

    def _padding_right_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for padding one block right of another."""
        pairs = self._block_pairs(DrawingCell.blocks_right)
        for block_under, block_over in pairs:
            pad = block_under.box.padding_right
            yield block_under.box.xmax >= block_over.box.xmax + pad

    def _block_pairs(
            self,
            get_blocks: Callable[[DrawingCell], Iterable[DrawingBlock]],
    ) -> Iterator[Tuple[DrawingBlock, DrawingBlock]]:
        """Return pairs of blocks overlapping at one side.

        'get_blocks' is the function that will be used to retrieve the
        blocks from each cell.

        """
        done = set()
        for cell in self._cells():
            blocks = list(get_blocks(cell))
            for i, block_under in enumerate(blocks[:-1]):
                block_over = blocks[i + 1]
                pair = (block_under, block_over)
                if pair not in done:
                    yield pair
                    done.add(pair)

    def _cells(self) -> Iterator[DrawingCell]:
        """Return the cells, row first."""
        for cells in self._cell_rows:
            yield from cells

    def _wire_segments(self) -> Iterator[DrawingWireSegment]:
        """Return the segments of all the wires."""
        for wire in self._wires():
            yield from wire

    def _wires(self) -> Iterator[DrawingWire]:
        """Return the wires."""
        for net in self._networks:
            yield from net
