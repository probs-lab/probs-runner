probs-runner
============

This repository contains `probs-runner`, a Python package for data processing using the ["Physical Resources Observatory" (PRObs) ontology system](https://github.com/ukfires/probs-ontology/). The Python package coordinates running the [RDFox triple store](https://www.oxfordsemantic.tech/product). 

About the project
-----------------

This ontology is being developed as part of [UK FIRES](https://ukfires.org).

Getting started
---------------

TODO: examples/tutorial.

{doc}`API reference <api>`

Compatibility with `probs-ontology` scripts
-------------------------------------------

`probs-docs` commit `46256fac3d5dfa6d3fce769e03464c9574ae3e78` or later is required.

`probs-runner` makes the following assumptions about the `probs-ontology` scripts files:

- All scripts and ontology files needed by RDFox are in `scripts/`.

For data conversion, the following files are overwritten based on the datasources passed to {py:func}`~probs_runner.probs_convert_data`

- `scripts/data-conversion/load_data.rdfox`
- `scripts/data-conversion/map.dlog`

Then, the file `scripts/data-conversion/master` is run.

For data enhancement, the script `scripts/data-enhancement/load_rdfox.rdfox` is overwritten to load the input data. Then, the file `scripts/data-enhancement/master` is run.

For data validation, input is configured the same as for data enhancement (but overwriting `scripts/data-validation/load_data.rdfox`). The file `scripts/data-validation/master` is run.

To run the endpoint, the script `scripts/reasoning/load_data.rdfox` is overwritten to load the input files. Then, the endpoint port is set according to the value passed to {py:func}`~probs_runner.probs_endpoint`, and the file `scripts/reasoning/master` is run.
