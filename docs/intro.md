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

`probs-docs` commit `8cc30d6daa37fa3d6d7508e87e8ae956f8023478` or later is required.

`probs-runner` makes the following assumptions about the `probs-ontology` scripts files:

- All scripts and ontology files needed by RDFox are in `scripts/`.
- Data files are in `data/`

The following files are overwritten based on the datasources passed to {py:func}`~probs_runner.probs_convert_data` and similar methods:

- `scripts/data-conversion/load_data.rdfox`
- `scripts/data-conversion/load_rules.rdfox`

Then, the file `scripts/data-conversion/master` is run.

Other modules (`data-enhancement`, `data-validation`, `reasoning`) work analogously.
