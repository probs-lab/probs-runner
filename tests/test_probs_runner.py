# -*- coding: utf-8 -*-

import shutil
from pathlib import Path
import gzip
from io import BytesIO

from rdflib import Namespace, Graph, Literal

import pytest

from probs_runner import (
    PROBS,
    load_datasource,
    probs_convert_data,
    probs_enhance_data,
    probs_endpoint,
    probs_answer_query,
)


NS = Namespace("https://ukfires.org/probs/ontology/data/simple/")


def test_convert_data_csv(tmp_path, script_source_dir):
    source = load_datasource(Path(__file__).parent / "sample_datasource_simple")
    output_filename = tmp_path / "output.nt.gz"
    probs_convert_data(
        [source], output_filename, tmp_path / "working", script_source_dir
    )
    assert output_filename.stat().st_size > 0

    # Should check for success or failure

    result = Graph()
    with gzip.open(output_filename, "r") as f:
        result.parse(f, format="nt")

    # TODO: should make the test case use the proper ontology
    assert (NS["Object-Bread"], PROBS.hasValue, Literal(6.0)) in result


def test_convert_data_ttl(tmp_path, script_source_dir):
    source = load_datasource(Path(__file__).parent / "sample_datasource_ttl")
    output_filename = tmp_path / "output.nt.gz"
    probs_convert_data(
        [source], output_filename, tmp_path / "working", script_source_dir
    )

    # Should check for success or failure

    result = Graph()
    with gzip.open(output_filename, "r") as f:
        result.parse(f, format="nt")

    # TODO: should make the test case use the proper ontology
    assert (NS["Object-Bread"], PROBS.hasValue, Literal(6.0)) in result


def test_convert_data_large_data_size(tmp_path, script_source_dir):
    # Sometimes with big data files it seems that there can be a delay between
    # RDFox finishing and the data actually being written.

    # Generate a bigger data file in a copy of the data source
    initial_datasource = Path(__file__).parent / "sample_datasource_simple"
    temp_datasource = tmp_path / "datasource"
    shutil.copytree(initial_datasource, temp_datasource)

    with open(temp_datasource / "data.csv", "wt") as f:
        f.write("Object,Value\n")
        for i in range(100000):
            f.write(f"Object{i},{i}\n")

    source = load_datasource(temp_datasource)

    output_filename = tmp_path / "output.nt.gz"
    probs_convert_data(
        [source], output_filename, tmp_path / "working", script_source_dir
    )
    assert output_filename.stat().st_size > 0


def test_enhance_data(tmp_path, script_source_dir):
    original_filename = tmp_path / "original.nt.gz"
    enhanced_filename = tmp_path / "enhanced.nt.gz"
    with gzip.open(original_filename, "wt") as f:
        f.write(
            """
<https://ukfires.org/probs/ontology/data/simple/Object-Bread> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://ukfires.org/probs/ontology/Object> .
        """
        )

    probs_enhance_data(
        original_filename,
        enhanced_filename,
        tmp_path / "working_enhanced",
        script_source_dir,
    )

    with gzip.open(enhanced_filename, "rt") as f:
        lines = f.readlines()

    # Check something has been added...
    assert len(lines) > 1


def _setup_test_nt_gz_data(p, object_name):
    p.parent.mkdir(exist_ok=True, parents=True)
    with gzip.open(p, "wt") as f:
        f.write(
            f"""
<https://ukfires.org/probs/ontology/data/simple/{object_name}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://ukfires.org/probs/ontology/Object> .
"""
        )


def _setup_test_ttl_data(p, object_name):
    p.parent.mkdir(exist_ok=True, parents=True)
    with open(p, "wt") as f:
        f.write(
            f"""
@prefix simple: <https://ukfires.org/probs/ontology/data/simple/> .
@prefix probs: <https://ukfires.org/probs/ontology/> .
simple:{object_name} a probs:Object .
"""
        )


def test_enhance_data_multiple_inputs(tmp_path, script_source_dir):
    original_filename_1 = tmp_path / "original1.nt.gz"
    original_filename_2 = tmp_path / "original2.ttl"
    enhanced_filename = tmp_path / "enhanced.nt.gz"

    _setup_test_nt_gz_data(original_filename_1, "Object-Bread")
    _setup_test_ttl_data(original_filename_2, "Object-Cheese")

    probs_enhance_data(
        [original_filename_1, original_filename_2],
        enhanced_filename,
        tmp_path / "working_enhanced",
        script_source_dir,
    )

    with gzip.open(enhanced_filename, "rt") as f:
        result = f.read()

    # Check something has been added...
    assert "Object-Bread>" in result
    assert "Object-Cheese>" in result


def test_enhance_data_multiple_inputs_with_name_clash(tmp_path, script_source_dir):
    original_filename_1 = tmp_path / "dir1" / "original.nt.gz"
    original_filename_2 = tmp_path / "dir2" / "original.nt.gz"
    enhanced_filename = tmp_path / "enhanced.nt.gz"

    _setup_test_nt_gz_data(original_filename_1, "Object-Bread")
    _setup_test_nt_gz_data(original_filename_2, "Object-Cheese")

    probs_enhance_data(
        [original_filename_1, original_filename_2],
        enhanced_filename,
        tmp_path / "working_enhanced",
        script_source_dir,
    )

    with gzip.open(enhanced_filename, "rt") as f:
        result = f.read()

    # Check something has been added...
    assert "Object-Bread>" in result
    assert "Object-Cheese>" in result


@pytest.fixture
def test_data_gz(tmp_path):
    output_filename = tmp_path / "output.nt.gz"
    with gzip.open(output_filename, "wt") as f:
        f.writelines(
            [
                '<https://ukfires.org/probs/ontology/data/simple/Object-Bread> <https://ukfires.org/probs/ontology/hasValue> "6"^^<http://www.w3.org/2001/XMLSchema#double> .',
                '<https://ukfires.org/probs/ontology/data/simple/Object-Cake> <https://ukfires.org/probs/ontology/hasValue> "3"^^<http://www.w3.org/2001/XMLSchema#double> .',
            ]
        )
    return output_filename


def test_probs_endpoint(tmp_path, test_data_gz, script_source_dir):

    # Now query the converted data
    query = "SELECT ?obj ?value WHERE { ?obj :hasValue ?value } ORDER BY ?obj"
    with probs_endpoint(
        test_data_gz, tmp_path / "working_reasoning", script_source_dir, port=12159
    ) as rdfox:
        result = rdfox.query_records(query)

        assert result == [
            {"obj": NS["Object-Bread"], "value": 6.0},
            {"obj": NS["Object-Cake"], "value": 3.0},
        ]


def test_probs_answer_query_file(test_data_gz, script_source_dir):
    f = BytesIO()
    query = "SELECT ?value WHERE { ?obj :hasValue ?value } ORDER BY ?value LIMIT 1"
    probs_answer_query(test_data_gz, query, f, script_source_dir=script_source_dir)
    assert f.getvalue() == b"?value\n3e+0\n"


@pytest.mark.parametrize("format,expected", [
    ("csv", b"value\r\n3\r\n"),
    ("json", b'{ "head":'),
])
def test_probs_answer_query_file_formats(test_data_gz, script_source_dir, format, expected):
    f = BytesIO()
    query = "SELECT ?value WHERE { ?obj :hasValue ?value } ORDER BY ?value LIMIT 1"
    probs_answer_query(test_data_gz, query, f, answer_format=format, script_source_dir=script_source_dir)
    assert f.getvalue().startswith(expected)


def test_probs_answer_query_path(tmp_path, test_data_gz, script_source_dir):
    query = "SELECT ?value WHERE { ?obj :hasValue ?value } ORDER BY ?value LIMIT 1"
    output = tmp_path / "result.nt"
    probs_answer_query(test_data_gz, query, output, script_source_dir=script_source_dir)
    assert output.read_bytes() == b"?value\n3e+0\n"
