Diagram definition file
=======================

Orthogram uses YAML for its input file format.  Of course, YAML being
a superset of JSON, you can use JSON if you prefer so.  The top-level
structure must be a YAML mapping; the program recognizes the following
keys, each one containing a different category of definitions:

* ``diagram``
* ``rows``
* ``blocks``
* ``connections``
* ``styles``
* ``groups``
* ``include``

diagram
-------

The ``diagram`` section contains the :ref:`Attributes` of the diagram
itself.  It is entirely optional; you do not need one if you do not
intend to customize your diagram.  Here is an example of a ``diagram``
section:

.. code-block:: yaml

   diagram:
     label: This is my diagram!
     label_position: bottom
     font_weight: bold

The optional label of the diagram is the title of the drawing.  If you
want a label with more than one line of text, use the newline
character in the string:

.. code-block:: yaml

   diagram:
     label: "Two lines separated by\na newline character"

For longer texts, the YAML literal style may be more convenient:

.. code-block:: yaml

   diagram:
     label: |-
       You can also use
       YAML literal style

Consult the :ref:`Attributes` section for a list of attributes
available for diagrams.  Out of all those attributes, however, the
following are of particular significance to the program:

``collapse_connections``
  If you set this to ``true``, collinear segments of connections
  belonging to the same ``group`` will collapse into a single segment.
  This may help reduce the clutter, though it depends on the
  application.  Try it out and see.

``scale``
  Use this attribute to scale the output image by a factor you
  specify.  E.g. ``scale: 1.5`` will produce an image enlarged by 50%.
  The default value is 1 (i.e. no scaling).

rows
----

The ``rows`` section of the diagram definition file defines the layout
of the diagram.  It is essential; without one, the program cannot
determine the position of any element to draw!

The program lays out the elements of the diagram in a rectangular
grid.  The grid consists of *cells*, which are arranged in rows and
columns.  You define the grid one row at a time.

The ``rows`` structure is a sequence of row definitions.  Each row
definition is a sequence of strings.  Each string corresponds to one
cell in the row.  If the string is neither null nor empty the cell is
*tagged* with the string; otherwise it is an anonymous cell.  Here is
an example:

.. code-block:: yaml

   rows:
     - [a, ~ , c, c]
     - [b, "", c, c]

The grid above contains a cell tagged with "a", another one tagged
with "b", two anonymous cells, and four cells tagged with "c".

You use the tags to refer to a cell or group of cells.  More
precisely, you use the tags to define the shape and position of the
blocks, which is the subject of the section that follows.

Note that, since the grid is rectangular, all the rows must contain
the same number of cells, which is the length of the longest row in
the definition.  You do not have to worry about it, though; the
program will pad shorter rows with anonymous cells, until all rows
have the same length.

Of course, using a text editor to manipulate the layout of the diagram
can quickly become cumbersome, especially when the diagram grows
large.  To counter this, Orthogram provides the option to define the
rows of the diagram in a separate CSV file.  Maintaining a CSV file is
quite easy using a spreadsheet program, like `LibreOffice Calc`_.
Please read the chapter on the :ref:`include` section to find out how
you can add a reference to an external CSV file in your DDF.

.. _LibreOffice Calc: https://www.libreoffice.org/

blocks
------

Each block occupies a rectangular area of the diagram grid.  You must
have at least a couple of blocks to produce a meaningful diagram.

The ``blocks`` section contains a sequence of block definitions.  Here
is an example:

.. code-block:: yaml

   blocks:

     - name: a
       label: A block named 'a'

     - label: An anonymous block
       tags: [b1, b2]
       stroke: [0, 0, 1]

Note that if you do not define a label for a block, the program will
use its name as a label instead.

A block occupies the minimal rectangular area of the grid that
contains all the cells tagged with the name of the block.  In the
example that follows, block "a" is just one cell, whereas block "b"
covers six cells, including the cell on which "a" stands:

.. code-block:: yaml

   rows:
     - [b, a   ]
     - [~, ~, b]

   blocks:

     - name: b
       label: A block of 6 cells

     - name: a
       label: A single-cell block

Note that, in the example above, the definition of block "b" comes
*before* the definition of block "a".  This is important, because the
program draws the blocks in the order they appear in the definition
file.  We do not want block "b" to hide block "a" under it!  What is
more, the program will apply *padding* around block "a" (the amount of
padding depends on the values of the ``padding_*`` attributes of block
"b").  The final image will be of block "a" lying *inside* block "b",
which is what one actually wants in situations like this.

If you want to expand a block beyond the cells tagged with its own
name, you can add more tags to it using the ``tags`` pseudo-attribute:

.. code-block:: yaml

   rows:
     - [a, ~, b]
     - [a, ~, c]
     - [a      ]
   blocks:
     - name: a
       tags: [b, c]
       label: Covers 9 cells!

Tags that are neither names of blocks nor mentioned in a ``tags``
sequence are "leftover" tags.  The program does not throw them away.
Instead, it uses them to *autogenerate* blocks, one block for each
unique tag.  These automatically generated blocks come with default
attributes and are labelled with their name.  This can be convenient
when constructing simple diagrams.  The example below is a complete,
self-contained diagram definition, without a ``blocks`` section in it:

.. code-block:: yaml

   rows:
     - [a, b]
   connections:
     - start: a
       end: b

connections
-----------

The ``connections`` section defines the connections between the
blocks.  It is a sequence of connection definitions.  Each definition
must declare the ``start`` and the ``end`` of the connection; it may
also include any :ref:`Attributes` appropriate for connections.  Here
is an example:

.. code-block:: yaml

   rows:
     - [a, b]
     - [~, c]

   connections:

     - start: a
       end: b
       stroke: [0, 0, 1]

     - start: b
       end: c
       stroke: [1, 0.5, 0.25]

Regarding the value of the ``start`` and ``end`` pseudo-attributes, it
can be one of the following:

* A block name.
* A sequence of block names.
* A mapping from block names to cell tags.

.. code-block:: yaml

   connections:

     # This will create six connections.

     - start: [a, b]
       end: [c, d, e]

     # This will create four connections starting from cell "x" under
     # block "f".  The second and third connections also aim at
     # specific tagged cells under "h" and "i".  The target of the
     # first and last connections are just blocks "g" and "j".

     - start: {f: x}
       end: {g, h: y, i: z, j}

The order of the connection definitions is important, because the
program draws the connections in the order that they appear in the
definition file.

Since it is not easy to avoid the intersection of connection lines in
complex diagrams, it is better that you draw intersecting connections
with a different ``stroke`` color to make obvious that the connection
lines are not connected at the intersection points.

Another way to avoid intersecting connection lines appearing as if
they were connected at the intersections is to draw a *buffer* around
the lines.  Attributes ``buffer_fill`` and ``buffer_width`` control
the appearance of the buffer.  By default, the program draws the
connections without a buffer.

Connections may have an additional ``group`` pseudo-attribute, which
works together with the ``collapse_connections`` diagram attribute.
If ``collapse_connections`` is set to true, connections of the same
group that run along the same axis can be drawn on top of each other,
thus reducing the clutter and size of the diagram.  The ``group``
value is just a string.  Note that setting this attribute affects the
drawing order of the connections.  When the program encounters a
connection marked with a group name, it draws all other connections
that belong to the same group immediately after the first one.  The
order of groups thus becomes more significant compared to the order of
the connections themselves.  It is probably good practice to keep
connection definitions referring to the same group close together in
the file.

You can add labels to connections in a manner similar to blocks.  A
connection can have up to three labels: a *start* label, which is
drawn near the first point of the connection, an *end* label, which is
drawn near the last point, and a *middle* label, which is drawn
somewhere between the other two.

The ability to have more than one label on a connection introduces
some necessary complexity to the definition.  Each label is a separate
element of the diagram inside the connection element, which acts as
its parent.  Each label element can have its own attributes.  You can
define text attributes on the connection itself; if you do so, the
values of the attributes in the connection serve as default values for
the corresponding attributes in the label elements.

To add labels to a connection, use the following elements:

* ``start_label``
* ``middle_label``
* ``end_label``

The following example demonstrates how to use them:

.. code-block:: yaml

   connections:

     - start: A
       end: B
       text_fill: [1, 0, 0]
       start_label: Start
       middle_label: Somewhere in between
       end_label:
         label: End
	 text_fill: [0, 0, 1]
	 text_orientation: vertical

The example can be explained as follows:

* The ``text_fill`` attribute of the connection defines a default
  color for all the labels, which is red.
* The ``label`` attribute is not defined on the connection itself.  If
  it were, it whould serve as the default text for all three labels.
* The values of the ``start_label`` and ``middle_label`` elements are
  plain strings.  This is shorthand we can use when there is no need
  to override attributes for a label.
* The ``end_label`` element overrides the value of the ``text_fill``
  attribute of the connection; the label is drawn in blue.  It also
  forces the label to be horizontal, regardless of the orientation of
  the connection segment over which it is drawn.

Note that if you define the ``label`` attribute on a connection, the
program will implicitly set the middle label with it, i.e. the middle
label is the default label for a connection.  The definitions in the
following example all have the exact same result:

.. code-block:: yaml

   connections:

     - start: A
       end: B
       middle_label:
         label: Some text

     - start: A
       end: B
       middle_label: Some text

     - start: A
       end: B
       label: Some text

styles
------

You can add style definitions to the ``styles`` section to create
named styles that the elements of the diagram (blocks, connections and
groups) can refer to.  Each style definition consists of attribute
key-value pairs.  For example, the following two blocks are drawn in
the same color:

.. code-block:: yaml

   blocks:

     - name: a
       style: reddish

     - name: b
       style: reddish

   rows:
     - [a, b]

   styles:

     reddish:
       stroke: [0.5, 0, 0]
       stroke_width: 3
       fill: [1, 0.85, 0.85]

You add style references to an element using the ``style`` attribute.
The value of this attribute can be either a single style name or a
sequence of style names.  Styles in a sequence override the ones
coming before them.  Attributes you define in the element itself
override the attributes it inherits from the referenced named styles.

There are two special style names, ``default_block`` and
``default_connection``, which you can use to set default values for
all the blocks and connections in the diagram.

Styles themselves *cannot* reference other styles, i.e. the program
ignores the ``style`` attribute in style definitions.

groups
------

You can use the ``groups`` section to attach attributes to connection
groups.  Since connections in the same group may collapse on one
another, it is usually desirable for all the connections in one group
to share the same attributes.  In the example that follows, all
connections are drawn in blue:

.. code-block:: yaml

   groups:

     water:
       stroke: [0, 0, 1]
       stroke_width: 4

   connections:

     - start: a
       end: b
       group: water

     - start: c
       end: d
       group: water

A group definition may contain references to named styles.  Note that
creating an entry in the ``groups`` section is not necessary for the
grouping of the connections; a common ``group`` name in each
connection definition is sufficient.

include
-------

Starting with version 0.5.4, Orthogram lets you split a diagram
definition into multiple files.  You can then compose the several
files into a single definition using ``include`` definitions in your
main DDF.

The facility is general and can be used recursively: you can include
other files in your included files and so on.  The program includes
each file just *once*, thus avoiding cyclical includes.  Note,
however, that deeply nested hierarchies can be confusing and you
should probably avoid them.  In particular, the sequence of merging
elements into the definition, though well defined, can lead to
surprising results.  The facility was actually implemented with the
following applications in mind:

* Sharing styles between diagrams
* Defining the diagram layout using CSV files

Although we describe the ``include`` section last, it is probably
better to put it at the top of the DDF.  The program merges included
files into the definition *before* considering any other section in
the file, so putting the ``include`` section at the top looks more
natural.  Within the ``include`` section of a file, the program merges
the included files in the order they appear.

This is an example that shows how you can include styles and row
definitions in your DDF:

.. code-block:: yaml

   include:

     - path: include/styles.yaml
     - path: include/rows.csv

Note that relative paths are relative to the location of the file that
includes them.  You may use absolute paths as well.

The program determines the type of the file (YAML or CSV) from the
extension of the file name.  If it ends in ``.csv`` or ``.txt``, the
program thinks it is a CSV rows file; otherwise it tries to load it as
a YAML file.  You can enforce the type using the ``type`` attribute:

.. code-block:: yaml

   include:

     - path: styles.txt
       type: yaml

     - path: rows
       type: csv

The character that delimits the block names in the CSV file is the
comma by default.  If you have a file with a different delimiter, you
can declare it using the ``delimiter`` attribute.  In the following
example, the row definitions file employs the tab character as the
delimiter [#]_:

.. code-block:: yaml

   include:

     - path: rows.txt
       delimiter: "\t"

.. [#] We should probably call this a *TSV* file, but people use the
       term "CSV" for any such file, regardless of the delimiter.
