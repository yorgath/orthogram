Orthogram
=========

Orthogram is a command line program and Python library that lets you
draw diagrams of graphs.  It reads the definition of a diagram from a
YAML file and produces a SVG file like this one:

.. image:: examples/powerplant.svg
   :width: 100%
   :alt: Diagram of a combined cycle power plant

Target audience
---------------

This project might be of interest to you if:

* You want to draw a network of boxes connected to each other with
  arrows.
* You do not want to use a GUI.  You prefer your diagrams defined in
  plain text files.
* You know where your boxes should be, but you would rather have the
  computer maintain the connections for you.
* You are not exploring the interconnections of thousands of nodes in
  random networks.  You are rather trying to prepare a slide for your
  little presentation or create a diagram for your software
  documentation project. A grid layout is probably all you need.
* You tried to force `Graphviz`_ to output the layout you want, but to
  no avail.

.. _Graphviz: https://graphviz.org/

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
