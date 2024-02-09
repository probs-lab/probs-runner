# Developing probs_runner

## Repository structure

- `docs` contains the documentation for the package.
- `src/probs_runner` contains Python code for setting up RDFox scripts.
- `tests` contains the tests.

## Documentation

Documentation is written using [jupyter-book](https://jupyterbook.org).

Install the Python package in a virtual environment with the necessary dependencies:

```shell
pip install -e '.[docs]'
```

Build the docs:

```shell
jupyter-book build docs
```

## Releases

To release a new version of the package:

- Ensure tests are passing, documentation and changelog is up to date.

- Bump the version number according to [semantic versioning](https://semver.org/), based on the type of changes made since the last release.

- Commit the new version and tag a release like "v0.1.2"

- Build the package: `python -m build`

- Publish the package to PyPI: `twine upload dist/probs_runner-[...]`

## Tests

Install the Python package in a virtual environment:

```shell
pip install -e '.[test]'
```

Make sure the correct version of RDFox is installed and on the path (e.g. with `pip install RDFox==6.3.1`)

Run the tests using pytest:

```shell
pytest
```

See [tests/README.md](tests/README.md) for more details of how to use the test runner.

### Structure for ontology scripts

Each probs-runner module (e.g. `data-conversion` or `kbc-hierarchy`) will require suitable scripts (and possibly data files) for use in running RDFox. Installation of the testing virtual environment described above will install scripts for use with the [Physical Resources Observatory \(PRObs\) Ontology](https://github.com/probs-lab/probs-ontology.git).
The folder containing the scripts and data needs to be structured as follows:

* script-source-folder-name
    * scripts
        * module1-name
            * master.rdfox
            * load\_data.rdfox
            * other scripts for module 1 ...
        * module2-name
            * master.rdfox
            * load\_data.rdfox
            * other scripts for module 2 ...
        * other modules ...
    * data


### Choosing the ontology scripts to use

The environment variable `PROBS_MODULE_PATH` can be set to specify the script source path(s). For example to specify the script sources to use when running the tests: 

```shell
PROBS_MODULE_PATH=/path/to/ontology-module-1:/path/to/probs-ontology pytest
```
 
The parameter `script_source_dir`, which can be passed to probs-runner functions such as ```probs_convert_data``` (see [runners.py](src/probs_runner/runners.py) for defined functions) or used on the `probs-runner` command line, can also be used to specify the script source paths. This parameter will override any value set for variable `PROBS_MODULE_PATH`.
To test probs-runner using this method to define script sources, edit the file [tests/conftest.py](tests/conftest.py) to specify the value for `script_src_dir`.

If no appropriate scripts are found in `script_source_dir` or `PROBS_MODULE_PATH` when running a module, probs-runner will look for installed scripts in a `probs_system` resource located in libraries containing installed Python packages (e.g. the `site-packages` folder).
