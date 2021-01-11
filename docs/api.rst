Python API
==========

Using the :py:class:`DiagramDef` class
--------------------------------------

If you want to create a diagram using Python, you can start by
creating an empty diagram definition object:

.. code-block:: python

   from orthogram import DiagramDef, write_svg

   d = DiagramDef(label="A hand-made diagram", text_fill="blue")

You can pass any diagram :ref:`Attributes` to the constructor as
key-value pairs.

You may add elements to the diagram definition in any order.  This is
how you define the layout grid, one row at a time:

.. code-block:: python

   d.add_row(["a"])
   d.add_row(["b", "", "c"])

The :py:meth:`add_row` method takes a list of cell tags.  Use an
empty string or None to insert a cell without a tag.

You define blocks using the :py:meth:`add_block` method:

.. code-block:: python

   d.add_block("a", label="Hello")
   d.add_block("b", label="Beautiful")
   d.add_block("c", tags=["c1", "c2"], label="World")

The first argument is the name of the block.  You can optionally
provide the tags of the cells that you want the block to cover
(besides the cells tagged with the name of the block), as well as
:ref:`Attributes` for the block as key-value pairs.

Use the :py:meth:`set_auto_block_attributes` method to set default
attributes for the blocks that the program creates automatically from
the "leftover" tags.

You create connections between blocks using the
:py:meth:`add_connection` method:

.. code-block:: python

   d.add_connection("a", "b", stroke="red")
   d.add_connection("c", ("d", "n"), stroke="blue")

The start and the end of the connection can be either a block name or
a pair of a block name and a cell tag.  Use the second form to target
specific cells of a block.  The :py:class:`DiagramDef` class offers an
:py:meth:`add_connections` method as well, which lets you create
connections en masse (all having the same attributes).  Use the Python
:py:func:`help()` function to learn more about it.

After you have finished building your diagram, use the
:py:func:`write_svg` function to write the SVG file:

.. code-block:: python

   write_svg(diagram, "hello.svg")

Using the :py:class:`Builder` class
-----------------------------------

The :py:class:`Builder` class lets you create a :py:class:`DiagramDef`
object from Python dictionaries like the ones you load from a YAML
file.  The :py:meth:`add` method imports a complete diagram
definition into the builder:

.. code-block:: python

   import yaml
   from orthogram import Builder, write_svg

   builder = Builder()
   with open("diagram.yaml") as f:
       data = yaml.safe_load(f)
       builder.add(data)
   write_svg(builder.diagram_def, "diagram.svg")

If you have to be more specific, :py:class:`Builder` provides the
following methods:

============================  ==========================
Do one                        Do many
============================  ==========================
:py:meth:`add_style`          :py:meth:`add_styles`
:py:meth:`add_group`          :py:meth:`add_groups`
:py:meth:`add_row`            :py:meth:`add_rows`
:py:meth:`add_block`          :py:meth:`add_blocks`
:py:meth:`add_connection`     :py:meth:`add_connections`
:py:meth:`configure_diagram`
============================  ==========================

For example:

.. code-block:: python

   block_def = {
       'label': "Hello",
       'fill': "yellow",
       'stroke': "none",
   }
   builder.add_block('hello', block_def)

Use the :py:func:`help` Python function to access the documentation
for each method.

The :py:attr:`diagram_def` property of a :py:class:`Builder` object
holds the definition for the diagram you are building.  If you want to
use the :py:class:`DiagramDef` API on it, as described in the previous
section, after or while using the builder, you can certainly do so.

Convenience functions
---------------------

The ``orthogram`` module provides the following functions as
shortcuts:

:py:func:`load_ddf`
   Loads a diagram definition file and returns a
   :py:class:`DiagramDef` object.

:py:func:`translate`
   Translates a diagram definition file to a SVG file directly.

:py:func:`translate_dir`
    Translates a whole directory of definition files.

The use of these functions is straightforward:

.. code-block:: python

   from orthogram import load_ddf, translate, translate_dir, write_svg

   # You can do this:
   d = load_ddf("diagram.yaml")
   write_svg(d, "diagram.svg")

   # also this:
   translate("diagram.yaml", "diagram.svg")

   # and even this:
   translate_dir("~/diagrams")
   
