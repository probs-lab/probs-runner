API Reference
=============

RDFlib namespaces
-----------------

.. py:data:: probs_runner.PROBS

   Namespace for the PRObs ontology.

.. py:data:: probs_runner.QUANTITYKIND

   Namespace for the QUDT `quantitykind` ontology.

.. py:data:: probs_runner.PROV

   Namespace for the `W3C PROV <https://www.w3.org/TR/prov-o/>`_ ontology.

.. py:data:: probs_runner.NAMESPACES

   Dictionary mapping default prefixes to namespaces. The prefixes available can
   be customised when calling :py:func:`probs_runner.probs_endpoint`.

Top-level functions
-------------------

.. automodule:: probs_runner
   :members: probs_convert_data, probs_validate_data, probs_enhance_data, probs_endpoint, connect_to_endpoint, answer_queries

Data sources
------------

.. autoclass:: probs_runner.Datasource
   :members: from_facts, from_files

.. autofunction:: probs_runner.load_datasource

PRObs endpoint
--------------

:py:class:`PRObsEndpoint` is a subclass of :py:class:`rdfox_runner.RDFoxEndpoint` which adds some more specialised query types.

.. autoclass:: probs_runner.PRObsEndpoint
   :members: get_observations
