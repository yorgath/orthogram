.. orthogram documentation master file, created by
   sphinx-quickstart on Sun Jan  3 14:16:42 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Orthogram
=========

Orthogram is a command line program and Python library that lets you
draw block diagrams.  It reads a YAML file and produces a PNG file
like this one:

.. image:: ../examples/showoff.png
   :width: 100%
   :alt: Complex diagram demonstrating the capabilities of the program

Orthogram does not aim to be a fully-featured graph layout solution.
It offers just a single layout: grid.  You have to arrange the blocks
manually in the grid and they stay fixed in place; the program will
not attempt to move them around trying to optimize any aspect of the
diagram.  Styling is also rather basic at the moment.  It does however
try to do a decent job arranging the connections around the blocks to
produce a tidy, readable drawing.

When used as a command line tool, Orthogram reads a *diagram
definition file* and produces a PNG image file.  The definition file
is written in YAML.

The source code is hosted on `Github`_.

.. _Github: https://github.com/yorgath/orthogram

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   install.rst
   cmd.rst
   hello.rst
   ddf.rst
   attributes.rst
   api.rst
   acknowledge.rst
   release.rst
   gallery.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
