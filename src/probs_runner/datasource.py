"""A Datasource collects information needed to load data into RDFox.

The data can in general include:
- Data files (e.g. csv or RDF data)
- RDFox load scripts
- Datalog rules

Each Datasource object bundles a set of these three data types together.

"""

import os
from dataclasses import dataclass, field
from hashlib import md5
from pathlib import Path
from io import StringIO
from typing import Union, Optional, IO, List

import logging
_logger = logging.getLogger(__name__)


FileSpec = Union[os.PathLike, str, IO]
FileSpecs = Union[List[FileSpec], FileSpec]

@dataclass
class Datasource:
    """Represent a set of inputs to RDFox.

    :param input_files: dictionary mapping identifiers (in the form of a
    filename with suitable extension) to Paths, or file-like objects, which need
    to be made available to RDFox.

    :param load_data_script: RDFox script to load data files.

    :param load_rules_script: RDFox script to load rules files.

    """

    input_files: dict = field(default_factory=dict)
    load_data_script: str = ""
    load_rules_script: str = ""

    @classmethod
    def from_facts(cls, facts: str):
        """Create a datasource from explicit list of facts."""
        hash = md5(facts.encode()).hexdigest()
        input_files = {
            f"data/{hash}.ttl": StringIO(facts)
        }
        import_statement = f"import {hash}.ttl\n"
        return cls(input_files, import_statement)

    @classmethod
    def from_files(cls,
                   input_files: Union[dict, list],
                   load_data_script: Optional[FileSpecs] = None,
                   load_rules_script: Optional[FileSpecs] = None,
                   data_subdir: Optional[str]=None):
        """Load a `Datasource` from specified files.

        The keys of `input_files` are the filenames to be referred to in the
        `load_data_script`; the values are the paths to the source file, or
        file objects to be read from directly.

        Alternatively, `input_files` can be a list, in which case the name
        (without directory) of each path is used as the copied filename. In this
        case file objects cannot be used, since they do not in general have a
        filename associated with them.

        In either case, the files specified in `input_files` are copied in to
        the RDFox working directory. If `data_subdir` is specified, data files
        are nested within `data/{data_subdir}`. The RDFox shell variable
        `dir.datasource` is set accordingly at the start of the `load_data` and
        `load_rules` scripts.

        The `load_data_script` passed as an argument is used if given.
        Otherwise, a load_data script is generated automatically to load any of
        `input_files` which can be directly read by RDFox (e.g. .ttl and .nt
        files, and their compressed versions).

        The `load_rules_script` passed as an argument is used if given.
        Otherwise, a load_rules script is generated automatically to load any of
        `input_files` which look like Datalog rules (i.e. files ending in
        .dlog).

        `load_data_script` and `load_rules_script` can be either a string or
        `pathlib.Path` path to be read, or a file-like object whose contents
        should be read. In addition a list of these can be passed, in which case
        their contents are concatenated.

        """

        if isinstance(input_files, list):
            input_files_list = input_files
            input_files = {}
            for source_path in input_files_list:
                if not isinstance(source_path, (str, Path)):
                    raise ValueError(
                        "Source paths in list must be filenames or Path objects. "
                        "Pass a dictionary to specify filenames for file inputs."
                    )
                source_path = Path(source_path)
                if source_path.name in input_files:
                    raise ValueError("Duplicate path name in list; use dict to specify "
                                     "different names")
                input_files[source_path.name] = source_path

        dest_dir = Path("data")
        if data_subdir is not None:
            dest_dir = dest_dir / data_subdir
            dir_setup = f'set dir.datasource "$(dir.facts)/{data_subdir}/"\n'
        else:
            dir_setup = 'set dir.datasource "$(dir.facts)/"\n'

        input_files = {Path(k): v for k, v in input_files.items()}

        full_input_files = {
            dest_dir / filename: input_file
            for filename, input_file in input_files.items()
        }

        # Keep track of files that haven't been used, if we are automatically
        # loading them.
        if load_data_script is None and load_rules_script is None:
            not_loaded_files = set(input_files.keys())
        else:
            not_loaded_files = set()

        _logger.debug("Trying to load automatically: %s", input_files.keys())
        if load_data_script is None:
            # Try to load automatically
            auto_input_data_files = [
                p
                for p in input_files
                if _can_load_data(p)
            ]
            _logger.debug("Automatically loading data: %s", auto_input_data_files)
            not_loaded_files -= set(auto_input_data_files)
            if auto_input_data_files:
                load_data_script_str = "# Auto generated to load data files\n" + "\n".join([
                    f'import "$(dir.datasource){p}"' for p in auto_input_data_files
                ])
            else:
                load_data_script_str = ""
        else:
            load_data_script_str = _paths_or_strs_to_str(load_data_script)

        if load_rules_script is None:
            # Try to load automatically
            auto_input_rules_files = [
                p
                for p in input_files
                if _can_load_rules(p)
            ]
            _logger.debug("Automatically loading rules: %s", auto_input_rules_files)
            not_loaded_files -= set(auto_input_rules_files)
            if auto_input_rules_files:
                load_rules_script_str = "# Auto generated to load rules files\n" + "\n".join([
                    f'import "$(dir.datasource){p}"' for p in auto_input_rules_files
                ])
            else:
                load_rules_script_str = ""
        else:
            load_rules_script_str = _paths_or_strs_to_str(load_rules_script)

        if not_loaded_files:
            _logger.warning(
                "No loading scripts given, and cannot automatically load some files: %s",
                not_loaded_files
            )
            raise ValueError(
                "No loading scripts given, and cannot automatically load some files: %s" %
                ", ".join(str(p) for p in not_loaded_files)
            )

        # Set the dir.datasource variable
        if load_data_script_str:
            load_data_script_str = dir_setup + load_data_script_str
        if load_rules_script_str:
            load_rules_script_str = dir_setup + load_rules_script_str

        return Datasource(full_input_files, load_data_script_str, load_rules_script_str)


def _can_load_data(path: Path):
    """Return True if RDFox can directly import this file as data."""
    if path.suffix == ".gz":
        path = path.with_suffix("")
    auto_suffices = {".ttl", ".nt"}
    return (path.suffix in auto_suffices)


def _can_load_rules(path: Path):
    """Return True if RDFox can directly import this file as rules."""
    if path.suffix == ".gz":
        path = path.with_suffix("")
    auto_suffices = {".dlog"}
    return (path.suffix in auto_suffices)


def _paths_or_strs_to_str(item_or_items: FileSpecs):
    items = (
        item_or_items if isinstance(item_or_items, list) else [item_or_items]
    )
    results = []
    for item in items:
        if hasattr(item, "read"):
            # XXX Issue with binary vs text-mode files?
            results += [item.read()]  # type: ignore
        else:
            results += [Path(item).read_text()]  # type: ignore
    return "\n".join(results)


def load_datasource(path: Path):
    """Load a `Datasource` from path."""

    if not isinstance(path, Path):
        path = Path(path)

    load_data_script = None
    load_rules_script = None

    if path.is_dir():
        load_data_path = path / "load_data.rdfox"
        if load_data_path.exists():
            load_data_script = load_data_path

        load_rules_path = path / "load_rules.dlog"
        if load_rules_path.exists():
            load_rules_script = load_rules_path

        allowed_extensions = {".csv", ".ttl", ".dlog"}
        data_files = [p for p in path.rglob("*.*") if p.suffix in allowed_extensions]

    elif path.exists():
        data_files = [path]

    else:
        raise FileNotFoundError(path)

    # Generate a unique id based on the full path
    datasource_id = md5(bytes(path)).hexdigest()

    datasource = Datasource.from_files(
        data_files, load_data_script, load_rules_script, data_subdir=datasource_id
    )
    return datasource
