Orthogram
=========

Orthogram is a command line program and Python library that lets you
draw block diagrams.  It reads the definition of a diagram from a YAML
file and produces a SVG file like this one:

.. image:: examples/showoff.svg
   :width: 100%
   :alt: (Showing off the capabilities)

Target audience
---------------

This project might be of interest to you if:

* You do not want to use a GUI.  You prefer your diagrams defined in
  plain text files.
* You know where your blocks should be, but you would rather have the
  computer maintain the connections for you.
* You tried to force `Graphviz`_ or `PlantUML`_ to output the layout
  you want, but to no avail.

.. _Graphviz: https://graphviz.org/
.. _PlantUML: https://plantuml.com/

Installation and usage
----------------------

Install from PyPI:

.. code::
   
   pip install orthogram

Assuming there is a diagram definition file named ``diagram.yaml`` in
your current directory, run the following command to produce a SVG
file:

.. code::
   
   python -m orthogram diagram.yaml

Please read the full online `documentation`_ for more.

.. _documentation: https://readthedocs.org/projects/orthogram/
