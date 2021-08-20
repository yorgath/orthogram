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
    Optional,
    Tuple,
)

from cassowary import Variable  # type: ignore
from cassowary.expression import Constraint  # type: ignore

from ..arrange import (
    ConnectionLabelPosition,
    Joint,
    Layout,
    RouteSegment,
    Wire,
    WireSegment,
)

from ..define import Block

from ..geometry import (
    Axis,
    IntPoint,
)

from ..util import (
    class_str,
    grid_str,
)

from .bands import Band
from .blocks import BlockBox

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
    Label,
)

######################################################################

class DrawingCell:
    """Cell in the drawing grid."""

    def __init__(self, point: IntPoint) -> None:
        """Initialize an empty cell."""
        self._point = point
        self._boxes_top: List[BlockBox] = []
        self._boxes_bottom: List[BlockBox] = []
        self._boxes_left: List[BlockBox] = []
        self._boxes_right: List[BlockBox] = []

    def __repr__(self) -> str:
        """Represent as string."""
        point = self._point
        i = point.i
        j = point.j
        content = f"i={i}, j={j}"
        return class_str(self, content)

    def boxes_top(self) -> Iterator[BlockBox]:
        """Iterate over the boxes at the top side of the cell."""
        yield from self._boxes_top

    def boxes_bottom(self) -> Iterator[BlockBox]:
        """Iterate over the boxes at the bottom side of the cell."""
        yield from self._boxes_bottom

    def boxes_left(self) -> Iterator[BlockBox]:
        """Iterate over the boxes at the left side of the cell."""
        yield from self._boxes_left

    def boxes_right(self) -> Iterator[BlockBox]:
        """Iterate over the boxes at the right side of the cell."""
        yield from self._boxes_right

    def place_box_top(self, box: BlockBox) -> None:
        """Place a box at the top side of the cell."""
        self._boxes_top.append(box)

    def place_box_bottom(self, box: BlockBox) -> None:
        """Place a box at the bottom side of the cell."""
        self._boxes_bottom.append(box)

    def place_box_left(self, box: BlockBox) -> None:
        """Place a box at the left side of the cell."""
        self._boxes_left.append(box)

    def place_box_right(self, box: BlockBox) -> None:
        """Place a box at the right side of the cell."""
        self._boxes_right.append(box)

######################################################################

class DrawingGrid:
    """Grid of the drawing."""

    def __init__(self, layout: Layout):
        """Initialize for a diagram layout."""
        self._layout = layout
        self._rows = self._make_rows()
        self._columns = self._make_columns()
        self._cell_rows = self._make_cells()
        self._block_boxes = self._make_block_boxes()
        self._block_box_map = self._make_block_box_map()
        self._joint_map = self._make_joint_map()
        self._networks = self._make_drawing_networks()
        self._wire_segment_map = self._make_wire_segment_map()
        self._route_segment_map = self._make_route_segment_map()
        self._axis_structures = self._make_axis_structures()
        self._apply_band_variables()
        self._apply_layer_variables()
        self._add_labels_to_wires()
        self._place_structures()
        self._connect_boxes()

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

    def block_boxes(self) -> Iterator[BlockBox]:
        """Iterate over the boxes of the diagram blocks."""
        yield from self._block_boxes

    def block_box(self, block: Block) -> BlockBox:
        """Return the box of the given block."""
        return self._block_box_map[block]

    def networks(self) -> Iterator[DrawingNetwork]:
        """Iterate over the networks of drawing wires."""
        yield from self._networks

    def constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the solver."""
        yield from self._block_box_constraints()
        yield from self._wire_constraints()
        yield from self._band_constraints()
        yield from self._padding_constraints()

    def optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the solver."""
        yield from self._block_box_optional_constraints()
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

    def _make_block_boxes(self) -> Sequence[BlockBox]:
        """Create boxes for the diagram blocks.

        The sequence of the boxes in the drawing is the same as the
        sequence of the corresponding blocks in the diagram.

        """
        boxes = []
        layout = self._layout
        dia = layout.diagram
        dia_attrs = dia.attributes
        wire_margin = dia_attrs.connection_distance
        lgrid = layout.grid
        rows = self._rows
        cols = self._columns
        for block in dia.blocks():
            bounds = lgrid.block_bounds(block)
            # It is possible that some blocks declared in the DDF are
            # not placed in the layout.
            if not bounds:
                continue
            top = rows[bounds.imin]
            bottom = rows[bounds.imax]
            left = cols[bounds.jmin]
            right = cols[bounds.jmax]
            label: Optional[Label] = None
            text = block.label()
            if text:
                attrs = block.attributes
                ori = block.label_orientation
                label = Label(text, ori, attrs, dia_attrs)
            box = BlockBox(
                block, top, bottom, left, right,
                wire_margin,
                label
            )
            self._associate_box_with_cells(box)
            boxes.append(box)
        return boxes

    def _associate_box_with_cells(self, box: BlockBox) -> None:
        """Associate the block box with the grid cells under it."""
        cells = self._cell_rows
        jmin = box.left_column.index
        jmax = box.right_column.index
        i = box.top_row.index
        for j in range(jmin, jmax + 1):
            cells[i][j].place_box_top(box)
        i = box.bottom_row.index
        for j in range(jmin, jmax + 1):
            cells[i][j].place_box_bottom(box)
        imin = box.top_row.index
        imax = box.bottom_row.index
        j = box.left_column.index
        for i in range(imin, imax + 1):
            cells[i][j].place_box_left(box)
        j = box.right_column.index
        for i in range(imin, imax + 1):
            cells[i][j].place_box_right(box)

    def _make_block_box_map(self) -> Mapping[Block, BlockBox]:
        """Map each diagram block to its corresponding box in the drawing."""
        result = OrderedDict()
        for box in self._block_boxes:
            result[box.block] = box
        return result

    def _make_joint_map(self) -> Mapping[Joint, DrawingJoint]:
        """Map each layout joint to a drawing joint."""
        result: MutableMapping[Joint, DrawingJoint] = OrderedDict()
        index = 0
        for net in self._layout.networks():
            for wire in net.wires():
                for seg in wire:
                    for ljoint in seg.joints:
                        if ljoint not in result:
                            result[ljoint] = DrawingJoint(ljoint)
                            index += 1
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
            attrs = lay_label.attributes
            ori = lay_segment.label_orientation
            label = Label(lay_label.text, ori, attrs, dia_attrs)
            draw_label: DrawingWireLabel
            if lay_label.position is ConnectionLabelPosition.MIDDLE:
                draw_label = DrawingWireMiddleLabel(
                    lay_label, label, cmin, cmax)
            else:
                draw_label = DrawingWireEndLabel(lay_label, label)
            draw_segment.add_label(draw_label)

    def _place_structures(self) -> None:
        """Associate wire structures to bands.

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
        """Return the wire structures."""
        for structs in self._axis_structures.values():
            yield from structs

    def _connect_boxes(self) -> None:
        """Connect the block boxes and the drawing segments."""
        box_map = self._block_box_map
        seg_map = self._wire_segment_map
        for lwire in self._layout_wires():
            sides = lwire.attachment_sides()
            conn = lwire.connection
            block_lsegs = [
                (conn.start.block, lwire[0], sides[0], True),
                (conn.end.block, lwire[-1], sides[-1], False),
            ]
            for block, lseg, side, out in block_lsegs:
                box = box_map[block]
                dseg = seg_map[lseg]
                box.attach_segment(dseg, side, out)

    def _block_box_constraints(self) -> Iterator[Constraint]:
        """Generate required constraints for the block boxes."""
        for box in self._block_boxes:
            yield from box.constraints()

    def _block_box_optional_constraints(self) -> Iterator[Constraint]:
        """Generate optional constraints for the block boxes."""
        for box in self._block_boxes:
            yield from box.optional_constraints()

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
        pairs = self._box_pairs(DrawingCell.boxes_top)
        for box_under, box_over in pairs:
            pad = box_under.padding_top
            yield box_under.ymin <= box_over.ymin - pad

    def _padding_bottom_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for padding one block under another."""
        pairs = self._box_pairs(DrawingCell.boxes_bottom)
        for box_under, box_over in pairs:
            pad = box_under.padding_bottom
            yield box_under.ymax >= box_over.ymax + pad

    def _padding_left_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for padding one block left of another."""
        pairs = self._box_pairs(DrawingCell.boxes_left)
        for box_under, box_over in pairs:
            pad = box_under.padding_left
            yield box_under.xmin <= box_over.xmin - pad

    def _padding_right_constraints(self) -> Iterator[Constraint]:
        """Generate constraints for padding one block right of another."""
        pairs = self._box_pairs(DrawingCell.boxes_right)
        for box_under, box_over in pairs:
            pad = box_under.padding_right
            yield box_under.xmax >= box_over.xmax + pad

    def _box_pairs(
            self,
            get_boxes: Callable[[DrawingCell], Iterable[BlockBox]],
    ) -> Iterator[Tuple[BlockBox, BlockBox]]:
        """Return pairs of boxes overlapping at the top side.

        'get_boxes' is the function that will be used to retrieve the
        boxes from each cell.

        """
        done = set()
        for cell in self._cells():
            boxes = list(get_boxes(cell))
            for i, box_under in enumerate(boxes[:-1]):
                box_over = boxes[i + 1]
                pair = (box_under, box_over)
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
