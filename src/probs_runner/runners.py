"""Functions for running RDFox with necessary input files and scripts, and
collecting results.

This aims to hide the complexity of setting up RDFox, loading data, adding
rules, answering queries, behind simple functions that map data -> answers.

The pipeline has multiple steps:
- The starting point are datasources (csv/loading rules)
- *Conversion* maps datasources to probs_original_data.nt.gz
- *Enhancement* maps probs_original_data.nt.gz to probs_enhanced_data.nt.gz
- We then start a *reasoning* endpoint to query the data

These correspond to the "basic" functions:
probs_convert_data(datasources) -> probs_original_data
probs_enhance_data(probs_original_data) -> probs_enhanced_data
probs_endpoint(probs_enhanced_data) -> endpoint

All of these functions accept some common options:
- working_dir
- script_source_dir

"""


from contextlib import contextmanager
import logging
from typing import Dict, ContextManager, Iterator, Iterable
from io import StringIO
import shutil
from pathlib import Path
from tempfile import mkdtemp
from hashlib import md5

try:
    import importlib.resources
    importlib_resources_files = importlib.resources.files
except (ImportError, AttributeError):
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources
    importlib_resources_files = importlib_resources.files

import pandas as pd

from rdfox_runner import RDFoxRunner, RDFoxEndpoint

from .datasource import Datasource
from .namespace import PROBS, NAMESPACES
from .endpoint import PRObsEndpoint

logger = logging.getLogger(__name__)




DEFAULT_PORT = 12112


def _standard_input_files(script_source_dir):
    if script_source_dir is None:
        # Use the version of the ontology scripts bundled with the Python
        # package
        try:
            script_source_dir = importlib_resources_files("probs_ontology")
        except ModuleNotFoundError:
            raise RuntimeError(
                "The probs_ontology package is not installed, and no script_source_dir has been specified."
            )

    if isinstance(script_source_dir, str):
        script_source_dir = Path(script_source_dir)

    # Standard files
    input_files = {
        "data/probs.fss": script_source_dir / "data/probs.fss",
        "data/additional_info.ttl": script_source_dir / "data/additional_info.ttl",
        "scripts/": script_source_dir / "scripts/",
        # "scripts/shared": script_source_dir / "scripts/shared",
        # "scripts/data-conversion": script_source_dir / "scripts/data-conversion",
    }

    return input_files


def _add_datasources_to_input_files(input_files, datasources):
    input_files["scripts/data-conversion/load_data.rdfox"] = StringIO(
        "\n".join(source.load_data_script for source in datasources)
    )
    input_files["scripts/data-conversion/map.dlog"] = StringIO(
        "\n".join(source.rules for source in datasources)
    )
    for datasource in datasources:
        for tgt, src in datasource.input_files.items():
            if tgt in input_files:
                raise ValueError(f"Duplicate entry in input_files for '{tgt}'")
            input_files[tgt] = src


def probs_convert_data(
    datasources,
    output_path,
    working_dir=None,
    script_source_dir=None,
) -> None:
    """Load `datasources`, convert to RDF and copy result to `output_path`.

    :param datasources: List of :py:class:`Datasource` objects describing inputs
    :param output_path: Path to save the data
    :param working_dir: Path to setup rdfox in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from
    """

    input_files = _standard_input_files(script_source_dir)
    _add_datasources_to_input_files(input_files, datasources)
    script = ["exec scripts/data-conversion/master"]

    import time
    runner = RDFoxRunner(input_files, script, working_dir=working_dir)
    with runner:
        logger.debug("probs_convert_data: RDFox runner done")
        logger.debug("probs_convert_data: data size %s", runner.files("data/probs_original_data.nt.gz").stat().st_size)
        time.sleep(0.001)
        logger.debug("probs_convert_data: data size %s", runner.files("data/probs_original_data.nt.gz").stat().st_size)
        time.sleep(0.01)
        logger.debug("probs_convert_data: data size %s", runner.files("data/probs_original_data.nt.gz").stat().st_size)
        time.sleep(0.1)
        logger.debug("probs_convert_data: data size %s", runner.files("data/probs_original_data.nt.gz").stat().st_size)
        shutil.copy(runner.files("data/probs_original_data.nt.gz"), output_path)
        logger.debug("probs_convert_data: Copy data done")

    # Should somehow signal success or failure


def probs_validate_data(
    original_data_path,
    working_dir=None,
    script_source_dir=None,
) -> None:
    """Load `original_data_path`, run data validation script.

    :param original_data_path: path to probs_original_data.nt.gz, or multiple paths to load
    :param working_dir: Path to setup runner in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from
    """

    input_files = _standard_input_files(script_source_dir)

    if isinstance(original_data_path, (list, tuple)):
        paths_to_load = []
        for path in (Path(x) for x in original_data_path):
            input_files["data/" + path.name] = path
            paths_to_load.append(path.name)
        input_files["scripts/data-validation/input.rdfox"] = StringIO(
            STANDARD_ENHANCEMENT_INPUT +
            "\n".join(f"import {name}" for name in paths_to_load)
        )
    else:
        input_files["data/probs_original_data.nt.gz"] = original_data_path

    script = ["exec scripts/data-validation/master"]

    with RDFoxRunner(input_files, script, working_dir=working_dir):
        logger.debug("probs_validate_data: RDFox runner done")
        # shutil.copy(rdfox.files("data/probs_enhanced_data.nt.gz"), output_path)
        # logger.debug("probs_validate_data: Copy data done")

    # Should somehow signal success or failure

# XXX This is a temporary hack -- the scripts should be updated to allow an easy customisation point
STANDARD_ENHANCEMENT_INPUT = """
# Import converted ontology and additional info
import probs.fss
import additional_info.ttl

# Load converted data
"""

def probs_enhance_data(
    original_data_path,
    output_path,
    working_dir=None,
    script_source_dir=None,
) -> None:
    """Load `original_data_path`, apply rules to enhance, and copy result to `output_path`.

    :param original_data_path: path to probs_original_data.nt.gz, or multiple paths to load
    :param output_path: path to save the data
    :param working_dir: Path to setup rdfox in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from
    """

    input_files = _standard_input_files(script_source_dir)

    if isinstance(original_data_path, (list, tuple)):
        paths_to_load = []
        for path in (Path(x) for x in original_data_path):
            # Keep path.name in the filename, so it's easier to understand, but
            # make sure it is unique using the full path hash.
            unique_filename = md5(bytes(path)).hexdigest() + "_" + path.name
            input_files["data/" + unique_filename] = path
            paths_to_load.append(unique_filename)
        input_files["scripts/data-enhancement/input.rdfox"] = StringIO(
            STANDARD_ENHANCEMENT_INPUT +
            "\n".join(f"import {name}" for name in paths_to_load)
        )
    else:
        input_files["data/probs_original_data.nt.gz"] = original_data_path

    script = ["exec scripts/data-enhancement/master"]

    import time
    runner = RDFoxRunner(input_files, script, working_dir=working_dir)
    with runner:
        logger.debug("probs_enhance_data: RDFox runner done")
        logger.debug("probs_enhance_data: data size %s", runner.files("data/probs_enhanced_data.nt.gz").stat().st_size)
        time.sleep(0.001)
        logger.debug("probs_enhance_data: data size %s", runner.files("data/probs_enhanced_data.nt.gz").stat().st_size)
        time.sleep(0.01)
        logger.debug("probs_enhance_data: data size %s", runner.files("data/probs_enhanced_data.nt.gz").stat().st_size)
        time.sleep(0.1)
        logger.debug("probs_enhance_data: data size %s", runner.files("data/probs_enhanced_data.nt.gz").stat().st_size)
        shutil.copy(runner.files("data/probs_enhanced_data.nt.gz"), output_path)
        logger.debug("probs_enhance_data: Copy data done")

    # Should somehow signal success or failure


@contextmanager
def probs_endpoint(
    enhanced_data_path,
    working_dir=None,
    script_source_dir=None,
    port=DEFAULT_PORT,
    namespaces=None,
    use_default_namespaces=True,
) -> Iterator:
    """Load `enhanced_data_path`, and start endpoint.

    This is a context manager. Use it as::

        with probs_endpoint(...) as rdfox:
            results = rdfox.query(...)

    :param enhanced_data_path: path to probs_original_data.nt.gz
    :param working_dir: Path to setup rdfox in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from
    :param port: Port number to listen on
    :param namespaces: dict of namespace mappings
    :param use_default_namespaces: whether to use the default namespaces.
    """

    if port is None:
        port = DEFAULT_PORT

    ns = NAMESPACES.copy() if use_default_namespaces else {}
    if namespaces is not None:
        ns.update(namespaces)

    input_files = _standard_input_files(script_source_dir)

    if isinstance(enhanced_data_path, (list, tuple)):
        paths_to_load = []
        for path in (Path(x) for x in enhanced_data_path):
            input_files["data/" + path.name] = path
            paths_to_load.append(path.name)
        input_files["scripts/reasoning/input.rdfox"] = StringIO(
            "\n".join(f"import {name}" for name in paths_to_load)
        )
    else:
        input_files["data/probs_enhanced_data.nt.gz"] = enhanced_data_path

    script = [
        f'set endpoint.port "{int(port)}"',
        "exec scripts/reasoning/master",
    ]

    endpoint = PRObsEndpoint(ns)
    with RDFoxRunner(
            input_files,
            script,
            working_dir=working_dir,
            wait="endpoint",
            endpoint=endpoint):
        yield endpoint


def probs_answer_query(
    inputs,
    query,
    output,
    answer_format=None,
    **kwargs,
):
    """Answer a single query using `probs_endpoint`.

    :param inputs: path or list of paths to input data/rules
    :param query: query text
    :param output: file or path to write result to
    :param answer_format: MIME type to request from RDFox

    Other keyword arguments are passed to `probs_endpoint`.
    """

    probs_answer_queries(inputs, [(query, output)], answer_format, **kwargs)


def probs_answer_queries(
    inputs,
    queries_outputs,
    answer_format=None,
    **kwargs,
):
    """Answer queries using `probs_endpoint`.

    :param inputs: path or list of paths to input data/rules
    :param queries_outputs: list of (query_text, output_file_or_path)
    :param answer_format: MIME type to request from RDFox

    Other keyword arguments are passed to `probs_endpoint`.
    """

    with probs_endpoint(inputs, **kwargs) as rdfox:
        for query, output in queries_outputs:
            res = rdfox.query_raw(query, answer_format=answer_format)
            write_output(res.iter_content(chunk_size=8192), output)


def write_output(stream: Iterable, output):
    """Write from `stream` to `output`, which can be a file or path.

    Paths ending in `.gz` are written with gzip compression.
    """
    if hasattr(output, "write"):
        for chunk in stream:
            output.write(chunk)
    elif str(output).endswith(".gz"):
        import gzip
        with gzip.open(output, "wb") as f:
            for chunk in stream:
                f.write(chunk)
    else:
        with open(output, "wb") as f:
            for chunk in stream:
                f.write(chunk)


def connect_to_endpoint(
        url,
        namespaces=None,
        use_default_namespaces=True,
) -> PRObsEndpoint:
    """Connect to an existing endpoint."""

    ns = NAMESPACES.copy() if use_default_namespaces else {}
    if namespaces is not None:
        ns.update(namespaces)

    endpoint = PRObsEndpoint(ns)
    endpoint.connect(url)
    return endpoint
