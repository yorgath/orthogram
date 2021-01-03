Command line interface
======================

The :py:mod:`orthogram` module is designed to be used from the command
line.  To generate a drawing of a diagram defined in a :ref:`Diagram
definition file` named ``diagram.yaml``, enter the following command:

.. code-block:: console

   $ python -m orthogram diagram.yaml

This will create a ``diagram.svg`` file in the same directory.  If you
wish to create a file with a different name or in a different
directory, pass the path as a second argument.

The program creates Scalable Vector Graphics (SVG) files.  Use your
web browser to view the drawing.  Use `Inkscape`_ to convert it to PNG
or other supported formats.

.. note::

   The character encoding of the definition file must be UTF-8.

.. _Inkscape: https://inkscape.org
