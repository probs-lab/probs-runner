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

`probs-runner` makes the following assumptions about the `probs-ontology` scripts files:

- `data/probs.fss` and `data/additional_info.ttl` are the ontology files needed by RDFox.
- All scripts in `scripts/` are needed by RDFox.

For data conversion, the following files are overwritten based on the datasources passed to {py:func}`~probs_runner.probs_convert_data`

- `scripts/data-conversion/load_data.rdfox`
- `scripts/data-conversion/map.dlog`

Then, the file `scripts/data-conversion/master` is run.

For data enhancement, if only one input file is needed, it is set up as `data/probs_original_data.nt.gz`, which is the default input filename. If multiple input files are needed, the script `scripts/data-enhancement/input.rdfox` is overwritten to load them. Currently, this hard-codes the loading of `probs.fss` and `additional_info.ttl`. Then, the file `scripts/data-enhancement/master` is run.

For data validation, input is configured the same as for data enhancement (but overwriting `scripts/data-validation/input.rdfox`). The file `scripts/data-validation/master` is run.

To run the endpoint, if only one input file is needed, it is set up as `data/probs_enhanced_data.nt.gz`, which is the default input filename. If multiple input files are needed, the script `scripts/reasoning/input.rdfox` is overwritten to load them. Then, the endpoint port is set according to the value passed to {py:func}`~probs_runner.probs_endpoint`, and the file `scripts/reasoning/master` is run.
