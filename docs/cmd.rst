Command line interface
======================

The :py:mod:`orthogram` module is designed to be used from the command
line.  To generate a drawing of a diagram defined in a :ref:`Diagram
definition file` named ``diagram.yaml`` in your current directory,
enter the following command:

.. code-block:: console

   $ python -m orthogram diagram.yaml

This will create a ``diagram.png`` image file in the same directory.
If you wish to create a file with a different name or in a different
directory, use the ``-o`` switch like this:

.. code-block:: console

   $ python -m orthogram diagram.yaml -o images/something.png

.. note::

   The character encoding of the definition file must be UTF-8.

.. _Inkscape: https://inkscape.org
