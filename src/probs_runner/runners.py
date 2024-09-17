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

import os
from contextlib import contextmanager
import logging
from typing import List, Dict, Iterable, Iterator, Union, Optional
from io import StringIO
from pathlib import Path
from hashlib import md5

try:
    # Try backported `importlib_resources` first if present.
    from importlib_resources import files as importlib_resources_files
    from importlib_resources.abc import Traversable
except (ImportError, AttributeError):
    from importlib.resources import files as importlib_resources_files
    from importlib.abc import Traversable

import pandas as pd

from rdfox_runner import RDFoxRunner

from .datasource import Datasource
from .namespace import NAMESPACES
from .endpoint import PRObsEndpoint
from .utils import prepare_file_for_rdfox, copy_from_rdfox

logger = logging.getLogger(__name__)


# Type aliases
AllowableDataInputs = Union[
    Datasource, str, Path, Iterable[Union[Datasource, str, Path]]
]

DEFAULT_PORT = 12112


def _standard_input_files(
    module_paths: Iterable[Path],
    module_name,
):

    # Find the module scripts in one of the paths given, or in the installed
    # `probs_system.scripts` namespace package.
    def _find_module_source():
        # Look in specified paths first
        for d in module_paths:
            p = d / "scripts" / module_name
            if p.exists():
                return p

        # Try to use the version of the module scripts bundled with the Python package
        try:
            d = importlib_resources_files("probs_system.scripts")
            if (d / module_name).exists():
                return d / module_name
        except ModuleNotFoundError:
            pass

        raise RuntimeError(
            f"The scripts for module '{module_name}' cannot be found. Try installing the "
            f"Python package 'probs-module-{module_name}', or specify the path to the module scripts?"
        )

    module_script_path = _find_module_source()

    # Standard files: scripts
    input_files: Dict[str, Union[Traversable, StringIO]] = {
        f"scripts/{module_name}": module_script_path,
    }

    # Add data files from explicit directories first
    for d in module_paths:
        path = d / "data"
        if path.exists():
            for p in path.iterdir():
                rel = str(Path("data") / p.relative_to(path))

                # FIXME: remove when RDFox supports gzip on Windows.
                # Work around [lack of] compression by RDFox: if needed, make a
                # copy of the data file that's [de]compressed
                p = prepare_file_for_rdfox(p, rel)

                input_files[str(rel)] = p

    # Use the version of the data bundled with the Python package, if available,
    # but don't overwrite files from explicit path above.
    try:
        data_source_dir = importlib_resources_files("probs_system.data")
    except ModuleNotFoundError:
        pass
    else:
        # Need to add data files individually by discovering which are available
        # (the MultiplexedPath from importlib.resources cannot be directly copied)
        if not isinstance(data_source_dir, Path):
            paths = data_source_dir._paths
        else:
            paths = [data_source_dir]
        for path in paths:
            for p in path.iterdir():
                rel = Path("data") / p.relative_to(path)

                # FIXME: remove when RDFox supports gzip on Windows.
                # Work around [lack of] compression by RDFox: if needed,
                # make a copy of the data file that's [de]compressed
                p = prepare_file_for_rdfox(p, rel)
                if str(rel) not in input_files.keys():
                    input_files[str(rel)] = p

    return input_files


def _add_datasource_to_input_files(
    input_files, load_data_script_file, load_rules_script_file, datasource
):
    load_data_script_file.write("\n\n### Datasource ###\n\n")
    load_data_script_file.write(datasource.load_data_script + "\n")

    load_rules_script_file.write("\n\n### Datasource ###\n\n")
    load_rules_script_file.write(datasource.load_rules_script + "\n")

    for tgt, src in datasource.input_files.items():
        if tgt in input_files:
            raise ValueError(f"Duplicate entry in input_files for '{tgt}'")

        # FIXME: remove when RDFox supports gzip on Windows.
        # Work around [lack of] compression by RDFox: if needed, make a copy of
        # the data file that's [de]compressed
        src = prepare_file_for_rdfox(src, tgt)

        input_files[tgt] = src


def _prepare_datasources_arg(datasources: AllowableDataInputs) -> List[Datasource]:
    """Convert the allowable inputs into a list of Datasources."""

    # Allow single values or a list
    ds_list = (
        [datasources]
        if isinstance(datasources, (Datasource, str, Path))
        else datasources
    )

    def _convert(ds) -> Datasource:
        if isinstance(ds, Datasource):
            return ds
        # Assume this is a data file to load. Keep the the filename, so it's
        # easier to understand, but place it in a uniquely-named subdirectory to
        # avoid clashing with other data files.
        bb = ds.encode("utf8") if isinstance(ds, str) else bytes(ds)
        subdir = md5(bb).hexdigest()
        return Datasource.from_files([ds], data_subdir=subdir)

    return [_convert(ds) for ds in ds_list]


def _setup_script_parameters(*args, **kwargs):

    # FIXME This is abusing the RDFox arguments, but it turns out that it
    # works to set a variable called "1" before calling an RDFox script with
    # no positional arguments, and the value of this variable appears as if
    # it was a positional argument.

    setup_script = []
    for idx, param in enumerate(args):
        setup_script.append(f'set {idx+1} "{param or ""}"')
    kwarg_pos = len(setup_script)
    for idx, key in enumerate(kwargs):
        setup_script.append(f'set {2*idx+kwarg_pos+1} "{key or ""}"')
        setup_script.append(f'set {2*idx+kwarg_pos+2} "{kwargs[key] or ""}"')
    return setup_script 

    
def probs_run_module(
    module: str,
    datasources: AllowableDataInputs,
    setup_script: Optional[Union[List[str], str]] = None,
    working_dir=None,
    script_source_dir=None,
    **kwargs,
) -> RDFoxRunner:
    """Set up RDFox to load `datasources` and run `module`.

    :param module: PRObs module to run

    :param datasources: List of :py:class:`Datasource` objects describing
    inputs, or `str` or `Path` paths to load from a directory or file.

    :param setup_script: Additional RDFox script to run before master script for
    the selected module, e.g. to set the listening port for the endpoint.

    :param working_dir: Path to setup rdfox in, defaults to a temporary
    directory

    :param script_source_dir: Path to copy scripts from

    """

    if setup_script is None:
        setup_script = []
    elif not isinstance(setup_script, list):
        setup_script = [setup_script]

    datasources = _prepare_datasources_arg(datasources)

    logger.debug("Running PRObs module %s (%s)", module, kwargs)

    # Backwards compatibility
    if script_source_dir is None:
        if "PROBS_MODULE_PATH" in os.environ:
            script_source_dir = os.environ["PROBS_MODULE_PATH"].split(os.pathsep)
        else:
            script_source_dir = []
    if isinstance(script_source_dir, (Path, str)):
        module_paths = [Path(script_source_dir)]
    else:
        module_paths = [Path(p) for p in script_source_dir]
    input_files = _standard_input_files(module_paths, module)

    # TODO: case where we want to pass multiple paths to load modules

    load_data_path = f"scripts/{module}/load_data.rdfox"
    load_rules_path = f"scripts/{module}/load_rules.rdfox"
    load_data_file = input_files[load_data_path] = StringIO()
    load_rules_file = input_files[load_rules_path] = StringIO()

    for datasource in datasources:
        logger.debug("Adding datasource: %s", datasource)
        _add_datasource_to_input_files(
            input_files, load_data_file, load_rules_file, datasource
        )

    load_data_file.seek(0)
    load_rules_file.seek(0)

    script = setup_script + [f"exec scripts/{module}/master"]

    runner = RDFoxRunner(input_files, script, working_dir=working_dir, **kwargs)
    return runner


def probs_convert_ontology(
    ontology: Union[os.PathLike, str],
    output_path: Union[os.PathLike, str],
    working_dir: Optional[Union[os.PathLike, str]] = None,
    script_source_dir: Optional[Union[os.PathLike, str]] = None,
) -> None:
    """Load a ontology.nt file, convert to Datalog rules and save to `output_path`.

    :param ontology: str contents or path to input ontology RDF data (e.g. `ontology.nt`)
    :param output_path: Path to save the resulting rules to
    :param working_dir: Path to setup rdfox in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from
    """

    datasources = [
        # The ontology data itself
        Datasource({"data/ontology.nt": ontology}),
    ]

    runner = probs_run_module(
        "ontology-conversion",
        datasources,
        working_dir=working_dir,
        script_source_dir=script_source_dir,
    )
    with runner:
        logger.debug("probs_convert_ontology: RDFox runner done")
        copy_from_rdfox(runner.files("data") / "probs_ontology_rules.dlog", output_path, timeout=10)
        logger.debug("probs_convert_ontology: Copy data done")

    # Should somehow signal success or failure


def probs_convert_data(
    datasources: AllowableDataInputs,
    output_path: Union[os.PathLike, str],
    working_dir: Optional[Union[os.PathLike, str]] = None,
    script_source_dir: Optional[Union[os.PathLike, str]] = None,
    fact_domain: Optional[str] = None,
) -> None:
    """Load `datasources`, convert to RDF and copy result to `output_path`.

    :param datasources: List of :py:class:`Datasource` objects describing
    inputs, or paths to individual input files.
    :param output_path: Path to save the data
    :param working_dir: Path to setup rdfox in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from
    :param fact_domain: RDFox fact domain to export
    """

    if fact_domain:
        setup_script = _setup_script_parameters("fact-domain", fact_domain)
    else:
        setup_script = None

    runner = probs_run_module(
        "data-conversion",
        datasources,
        setup_script=setup_script,
        working_dir=working_dir,
        script_source_dir=script_source_dir,
    )
    with runner:
        logger.debug("probs_convert_data: RDFox runner done")
        copy_from_rdfox(runner.files("data/probs_original_data.nt.gz"), output_path, timeout=10)
        logger.debug("probs_convert_data: Copy data done")

    # Should somehow signal success or failure


def probs_validate_data(
    datasources: AllowableDataInputs,
    working_dir: Optional[Union[os.PathLike, str]] = None,
    script_source_dir: Optional[Union[os.PathLike, str]] = None,
    debug_files: Optional[Union[os.PathLike, str]] = None,
) -> bool:
    """Load `original_data_path`, run data validation script.

    :param datasources: List of :py:class:`Datasource` objects describing
    inputs, or paths to individual input files.
    :param working_dir: Path to setup runner in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from
    :param debug_files: Path to folder for debug log files, defaults to no debugging
    """

    if debug_files is None:
        debug_param = "off"
    else:
        debug_files = Path(debug_files)
        debug_files.mkdir(parents=True, exist_ok=True)
        debug_param = "on"

    setup_script = _setup_script_parameters(debug=debug_param)

    runner = probs_run_module(
        "data-validation",
        datasources,
        setup_script=setup_script,
        working_dir=working_dir,
        script_source_dir=script_source_dir,
    )

    with runner:
        logger.debug("probs_validate_data: RDFox runner done")
        valid_file = runner.files("data") / "valid.log"
        result = valid_file.read_text().splitlines()
        if debug_files != None:
            copy_from_rdfox(valid_file, debug_files / "valid.log")
            copy_from_rdfox(runner.files("data") / "test_status.csv",
                            debug_files / "tests.csv")
            for output_file in runner.files("data").glob("test_*.log"):
                copy_from_rdfox(output_file, debug_files / output_file.name)
        if result[1] == "true":
            return True
        else:
            return False 


def probs_enhance_data(
    datasources: AllowableDataInputs,
    output_path: Union[os.PathLike, str],
    working_dir: Optional[Union[os.PathLike, str]] = None,
    script_source_dir: Optional[Union[os.PathLike, str]] = None,
) -> None:
    """Load input data, apply rules to enhance, and copy result to `output_path`.

    :param datasources: List of :py:class:`Datasource` objects describing
    inputs, or paths to individual input files.
    :param output_path: path to save the data
    :param working_dir: Path to setup rdfox in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from

    DEPRECATED: use `probs_kbc_hierarchy` instead.
    """
    probs_kbc_hierarchy(datasources, output_path, working_dir, script_source_dir)


def probs_kbc_hierarchy(
    datasources: AllowableDataInputs,
    output_path: Union[os.PathLike, str],
    working_dir: Optional[Union[os.PathLike, str]] = None,
    script_source_dir: Optional[Union[os.PathLike, str]] = None,
    *args,
    **kwargs,
) -> None:
    """Load input data, apply rules to enhance, and copy result to `output_path`.

    :param datasources: List of :py:class:`Datasource` objects describing
    inputs, or paths to individual input files.
    :param output_path: path to save the data
    :param working_dir: Path to setup rdfox in, defaults to a temporary directory
    :param script_source_dir: Path to copy scripts from
    :param variant: Category for KBC, e.g. "process" 
    """
 
    setup_script = _setup_script_parameters(*args, **kwargs)

    runner = probs_run_module(
        "kbc-hierarchy",
        datasources,
        setup_script=setup_script,
        working_dir=working_dir,
        script_source_dir=script_source_dir,
    )
    with runner:
        logger.debug("probs_enhance_data: RDFox runner done")
        copy_from_rdfox(runner.files("data/probs_enhanced_data.nt.gz"), output_path, timeout=10)
        logger.debug("probs_enhance_data: Copy data done")

    # Should somehow signal success or failure


@contextmanager
def probs_endpoint(
    datasources: AllowableDataInputs,
    working_dir: Optional[Union[os.PathLike, str]] = None,
    script_source_dir: Optional[Union[os.PathLike, str]] = None,
    port: Optional[int] = DEFAULT_PORT,
    namespaces: Optional[dict] = None,
    use_default_namespaces: bool = True,
) -> Iterator:
    """Load data sources, and start endpoint.

    This is a context manager. Use it as::

        with probs_endpoint(...) as rdfox:
            results = rdfox.query(...)

    :param datasources: List of :py:class:`Datasource` objects describing
    inputs, or paths to individual input files.
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

    setup_script = [
        f'set endpoint.port "{int(port)}"',
    ]

    endpoint = PRObsEndpoint(ns)
    runner = probs_run_module(
        "endpoint",
        datasources,
        setup_script,
        working_dir=working_dir,
        script_source_dir=script_source_dir,
        wait="endpoint",
        endpoint=endpoint,
    )
    with runner:
        yield endpoint


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


def answer_queries(rdfox, queries) -> Dict:
    """Answer queries from RDFox endpoint.

    :param rdfox: RDFox endpoint
    :param queries: Dict of {query_name: query_text}, or list of [query_text].
    :return: Dict of {query_name: result}
    """
    if isinstance(queries, list):
        queries = {i: query_text for i, query_text in enumerate(queries)}
    elif not isinstance(queries, dict):
        raise ValueError("query should be list or dict")

    answers_df = {
        query_name: rdfox.query_records(query_text)
        for query_name, query_text in queries.items()
    }

    with pd.option_context(
        "display.max_rows", 100, "display.max_columns", 10, "display.max_colwidth", 200
    ):
        for k, v in answers_df.items():
            logger.info("Results from query %s:", k)
            logger.info("\n%s", pd.DataFrame.from_records(v))

    return answers_df
