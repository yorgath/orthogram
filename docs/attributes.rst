Attributes
==========

The following table summarizes the attributes available to the diagram
and its components.  Where an attribute is applicable, it shows the
default value *in Python*.  In the YAML file, you just omit the
attribute or leave the value empty.  Also, in YAML you can have all
values in lowercase.  The *name* of the attribute *must be* lowercase
in both Python and YAML.

========================  ===============  ===============  ===============
Attribute                 Diagram          Block            Connection
========================  ===============  ===============  ===============
``arrow_aspect``                                            1.5
``arrow_back``                                              False
``arrow_base``                                              3.0
``arrow_forward``                                           True
``buffer_fill``                                             None
``buffer_width``                                            0.0
``collapse_connections``  False
``connection_distance``   4.0
``entrances``                                               [<all>]
``exits``                                                   [<all>]
``fill``                  [1.0, 1.0, 1.0]  None
``font_family``           "Arial"          "Arial"          "Arial"
``font_size``             14.0             10.0             10.0
``font_style``            NORMAL           NORMAL           NORMAL
``font_weight``           NORMAL           NORMAL           NORMAL
``label``                 None             None             None
``label_distance``        6.0              6.0              4.0
``label_position``        TOP              CENTER
``margin_bottom``                          24.0
``margin_left``                            24.0
``margin_right``                           24.0
``margin_top``                             24.0
``min_height``            256.0            48.0
``min_width``             256.0            96.0
``padding_bottom``        0.0              8.0
``padding_left``          0.0              8.0
``padding_right``         0.0              8.0
``padding_top``           0.0              8.0
``pass_through``                           False
``scale``                 1.0
``stroke_dasharray``      None             None             None
``stroke_width``          0.0              2.0              2.0
``stroke``                None             [0.0, 0.0, 0.0]  [0.0, 0.0, 0.0]
``text_fill``             [0.0, 0.0, 0.0]  [0.0, 0.0, 0.0]  [0.0, 0.0, 0.0]
``text_line_height``      1.2              1.2              1.2
``text_orientation``      HORIZONTAL       HORIZONTAL       FOLLOW
========================  ===============  ===============  ===============

Basic styling
-------------

stroke
~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: Sequence of 3-4 floats
* Default: "none" (D), "black" (B, C)

The ``stroke`` attribute defines the color of a line.  When used with
an area, it applies to the outline.  The value must be a sequence of
three to four numbers, each number being in the range between 0.0 and
1.0 inclusive.  The four numbers correspond to the color components in
the RGBA sequence.  The value for the A (alpha) component is optional,
the default being 1.0 (i.e. fully opaque).

stroke_width
~~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: Float
* Default: 0.0 (D), 2.0 (B, C)

The ``stroke_width`` attribute defines the width of a connection line
or box outline.  The value is in device units (i.e. pixels).

stroke_dasharray
~~~~~~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: Sequence of floats
* Default: None

The ``stroke_dasharray`` attribute defines a dash pattern for a line.
For example, a value of [6, 3] results in a pattern of dashes six
units long separated by gaps three units long.

fill
~~~~

* Applies to: Diagram and Blocks
* Type: Sequence of 3-4 floats
* Default: None

The ``fill`` attribute defines the color to fill areas with.

Text
----

label
~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: String
* Default: None

The ``label`` attribute defines the text to draw on a block or near a
connection line.  It is also used to add a title to the diagram.  The
value is a string that may consist of several lines separated by
newline characters.

Regarding blocks, if the label of a block is not defined, its name is
used instead.  To have a block without a label, an empty string must
be specified in the YAML file.

label_position
~~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: ``LabelPosition``
* Default: TOP (D), CENTER (B)

The ``label_position`` attribute defines the position of the label
inside a box.  The positions available for labels are:

* BOTTOM
* BOTTOM_LEFT
* BOTTOM_RIGHT
* CENTER
* TOP
* TOP_LEFT
* TOP_RIGHT

label_distance
~~~~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: Float
* Default: 6.0 (D, B), 4.0 (C)

The ``label_distance`` attribute defines the distance of a label from
the line relative to which it is drawn.  For diagrams and blocks, this
is the distance from the outline of the box.  For connections, the
distance is measured from the connection line.

text_fill
~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: Sequence of 3-4 floats
* Default: [0.0, 0.0, 0.0]

The ``text_fill`` attribute defines the color in which text is drawn.

text_orientation
~~~~~~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: ``TextOrientation``
* Default: HORIZONTAL (D, B), FOLLOW (C)

The ``text_orientation`` attribute defines the orientation in which
text is drawn.  If the value is ``VERTICAL``, the text is rotated 90
degrees anticlockwise.

Regarding connections, text orientation influences the algorithm
employed by the program to find an optimal position for the label of a
connection.  If the orientation of the text is set to ``HORIZONTAL``,
the program will attach the label to a horizontal segment, if there is
one; ``VERTICAL`` works in the same way.  However, there is a special
value available for the text orientation of connections, which is
``FOLLOW``.  This value means that the orientation of the label is the
same as the orientation of the segment to which it is attached.  The
algorithm is free to attach the label to any segment.  It is the
default value for connections.

text_line_height
~~~~~~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: Float
* Default: 1.2

The ``text_line_height`` attribute is used to set the spacing between
lines of text.  A value of 1.2 means that the distance between two
consecutive lines must be 20% of the height of the text itself.

font_family
~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: String
* Default: "Arial"

The ``font_family`` attribute is used to select a font for the label.
It is similar to the ``font-family`` property in CSS.  The default
font family is Arial, which should give similar results in both
Windows and Unix systems.

font_size
~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: Float
* Default: 14.0 (D), 10.0 (B, C)

The ``font_size`` attribute defines the size of the font in points.
It is equivalent to the ``font-size`` property in CSS.  Orthogram uses
a factor of 1.25 internally to convert points to device units
(i.e. one point equals 1.25 pixels).

font_style
~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: ``FontStyle``
* Default: NORMAL

The ``font_style`` attribute defines the style of the font used to
render text.  It is similar to the ``font-style`` property in CSS.
The following font styles are available:

* NORMAL
* ITALIC
* OBLIQUE

font_weight
~~~~~~~~~~~

* Applies to: Diagram, Blocks and Connections
* Type: ``FontWeight``
* Default: NORMAL

The ``font_weight`` attribute defines the weight of the font used to
render text.  It is similar to the ``font-weight`` property in CSS.
The value of the attribute may be one of the following:

* NORMAL
* BOLD

Arrows
------

arrow_forward
~~~~~~~~~~~~~

* Applies to: Connections
* Type: Boolean
* Default: True

If ``arrow_forward`` is true for a connection, the program draws an
arrow head at the end of the connection line.  This is the default.
This attribute is similar to the ``arrowforward`` attribute in
Graphviz.

arrow_back
~~~~~~~~~~

* Applies to: Connections
* Type: Boolean
* Default: False

If ``arrow_back`` is true for a connection, the program draws an arrow
head at the start of the connection line.  By default, the program
does *not* draw a back arrow.  This attribute is similar to the
``arrowback`` attribute in Graphviz.

arrow_base
~~~~~~~~~~

* Applies to: Connections
* Type: Float
* Default: 3.0

Attribute ``arrow_base`` controls the width of the arrow relative to
the width of the line.  The width of the base of the arrow is equal to
``arrow_base * stroke_width``.

arrow_aspect
~~~~~~~~~~~~

* Applies to: Connections
* Type: Float
* Default: 1.5

Attribute ``arrow_aspect`` controls the length of the arrow, which is
equal to ``arrow_aspect * arrow_base * stroke_width``.

Buffering
---------

buffer_width
~~~~~~~~~~~~

* Applies to: Connections
* Type: Float
* Default: 0.0

The ``buffer_width`` attribute defines the width of the buffer around
a connection line.  The default width is zero, i.e. no buffer is
drawn.

buffer_fill
~~~~~~~~~~~~

* Applies to: Connections
* Type: Sequence of 3-4 floats
* Default: None

The ``buffer_fill`` attribute defines the color of the buffer around a
connection line.  The default color is None, i.e. no buffer is
visible.

Maintaining distances
---------------------

connection_distance
~~~~~~~~~~~~~~~~~~~

* Applies to: Diagram
* Type: Float
* Default: 4.0

The ``connection_distance`` attribute is used to define the minimum
distance between connection lines.

margin_top
~~~~~~~~~~

* Applies to: Blocks
* Type: Float
* Default: 24.0

margin_bottom
~~~~~~~~~~~~~

* Applies to: Blocks
* Type: Float
* Default: 24.0

margin_left
~~~~~~~~~~~

* Applies to: Blocks
* Type: Float
* Default: 24.0

margin_right
~~~~~~~~~~~~

* Applies to: Blocks
* Type: Float
* Default: 24.0

The ``margin_*`` attributes are used to define the space around
blocks.  They are similar to the ``margin-*`` properties of CSS,
though they are used in a slightly different way.  In Orthogram they
are *additive*, i.e. if one block has a 12 unit right margin and the
block next to it has a 10 unit left margin, the distance between them
will be equal to 22 units.

padding_top
~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 0.0 (D), 8.0 (B)

padding_bottom
~~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 0.0 (D), 8.0 (B)

padding_left
~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 0.0 (D), 8.0 (B)

padding_right
~~~~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 0.0 (D), 8.0 (B)

The ``padding_*`` attributes define the distance between the border of
a box and its contents.  They are similar to the ``padding-*``
properties in CSS.

Sizing
------

min_width
~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 256.0 (D), 96.0 (B)

min_height
~~~~~~~~~~

* Applies to: Diagram and Blocks
* Type: Float
* Default: 256.0 (D), 48.0 (B)

The ``min_width`` and ``min_height`` attributes define lower limits
for the dimensions of boxes.  Note that Orthogram will make the size
of the diagram large enough to fit all the elements inside it, and
will also enlarge blocks as needed for the connections attached to
them.  These attributes are analogous to the ``minwidth`` and
``minheight`` attributes in Graphviz.

scale
~~~~~

* Applies to: Diagram
* Type: Float
* Default: 1.0

The ``scale`` attribute causes the image to be drawn scaled by the
specified factor.

Routing
-------

exits
~~~~~

* Applies to: Connections
* Type: Set of ``Side``
* Default: All possible values

entrances
~~~~~~~~~

* Applies to: Connections
* Type: Set of ``Side``
* Default: All possible values

The ``exits`` and ``entrances`` attributes control the routing of a
connection at the start and end points, respectively.  By default, the
program is free to start routing a connection from any side of the
source block, as well as end at any side of the destination block.
Using the aforementioned attributes, one can restrict the exit and
entrance sides.  The value is a set that may contain any of the
following values:

* BOTTOM
* LEFT
* RIGHT
* TOP

pass_through
~~~~~~~~~~~~

* Applies to: Blocks
* Type: Boolean
* Default: False

By default, a block does not permit connections to pass through it
unless they start or end within the block itself.  Setting
``pass_through`` to false makes a block permeable to all connections.

Grouping
--------

collapse_connections
~~~~~~~~~~~~~~~~~~~~

* Applies to: Diagram
* Type: Boolean
* Default: False

If the value of the ``collapse_connections`` diagram attribute is
true, parallel segments of connections in the same group are drawn on
top of each other.
