Python API
==========

Using the :py:class:`Diagram` class
-----------------------------------

If you want to create a diagram using Python, you can start by
creating an empty :py:class:`Diagram` object:

.. code-block:: python

   from orthogram import Diagram, write_svg

   diagram = Diagram(label="A hand-made diagram", text_fill="blue")

You can pass any diagram :ref:`Attributes` to the constructor as
key-value pairs.

You can now add terminals to the diagram:

.. code-block:: python

   diagram.add_terminal("a", label="Hello")
   diagram.add_terminal("b", label="Beautiful")
   diagram.add_terminal("c", label="World")

Again, you can provide :ref:`Attributes` for the terminals as
key-value pairs.  If you want to set default attributes for the new
terminals, use the :py:meth:`set_default_terminal_attributes()`
method.

In order to use the terminals, you must first place pins for them in
the grid:

.. code-block:: python

   diagram.add_row(["a"])
   diagram.add_row(["b", "", "c"])

The :py:meth:`add_row()` method takes a list of terminal names.  Note
that you must have added the terminals to the diagram before placing
pins for them in the grid.  Use an empty string or None to leave an
empty space between terminals.

After placing the terminals, you can connect them via links like this:

.. code-block:: python

   diagram.add_link("a", "b", stroke="red")

Note that the :py:class:`Diagram` class offers an
:py:meth:`add_links()` method as well, which lets you create links en
masse (all having the same attributes).

After you have finished building your diagram, use the
:py:func:`write_svg()` function to write the SVG file:

.. code-block:: python

   write_svg(diagram, "hello.svg")

Using the :py:class:`Builder` class
-----------------------------------

The :py:class:`Builder` class lets you create :py:class:`Diagram`
objects from Python dictionaries like the ones you load from a YAML
file.  The :py:meth:`add()` method imports a complete diagram
definition into the builder:

.. code-block:: python

   import yaml
   from orthogram import Builder, write_svg

   builder = Builder()
   with open("diagram.yaml") as f:
       data = yaml.safe_load(f)
       builder.add(data)
   write_svg(builder.diagram, "diagram.svg")

If you have to be more specific, :py:meth:`Builder` provides the
following methods:

==============================  ==========================
Do one                          Do many
==============================  ==========================
:py:meth:`add_style()`          :py:meth:`add_styles()`
:py:meth:`add_group()`          :py:meth:`add_groups()`
:py:meth:`add_terminal()`       :py:meth:`add_terminals()`
:py:meth:`add_row()`            :py:meth:`add_rows()`
:py:meth:`add_link()`           :py:meth:`add_links()`
:py:meth:`configure_diagram()`
==============================  ==========================

For example:

.. code-block:: python

   terminal_def = {
       'label': "Hello",
       'fill': "yellow",
       'stroke': "none",
   }
   builder.add_terminal('hello', terminal_def)

Use the :py:func:`help()` Python function to read the documentation of
each method.  Note that you have to do the imports in a logical order:
you must import the styles before using them, place the pins before
linking the terminals etc.

The :py:attr:`diagram` property of a :py:class:`Builder` object holds
the diagram which is being built.  If you want to use the
:py:class:`Diagram` API on it, as described in the previous section,
after or while using the builder, you can certainly do so.

Convenience functions
---------------------

The :py:func:`load_ddf()` and :py:func:`translate()` functions are
provided as shortcuts:

.. code-block:: python

   from orthogram import load_ddf, translate, write_svg

   # You can do this:
   diagram = load_ddf("diagram.yaml")
   write_svg(diagram, "diagram.svg")

   # or just this:
   translate("diagram.yaml", "diagram.svg")
