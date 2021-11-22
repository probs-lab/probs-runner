# -*- coding: utf-8 -*-

from pathlib import Path
import gzip

from rdflib import Namespace, Graph, Literal

from probs_runner import (
    PROBS,
    load_datasource,
    probs_convert_data,
    probs_enhance_data,
    probs_endpoint,
    answer_queries,
)


NS = Namespace("https://ukfires.org/probs/ontology/data/simple/")


def test_convert_data(tmp_path, script_source_dir):
    source = load_datasource(Path(__file__).parent / "sample_datasource_simple")
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


def test_probs_endpoint(tmp_path, script_source_dir):
    output_filename = tmp_path / "output.nt.gz"
    with gzip.open(output_filename, "wt") as f:
        f.writelines(
            [
                '<https://ukfires.org/probs/ontology/data/simple/Object-Bread> <https://ukfires.org/probs/ontology/hasValue> "6"^^<http://www.w3.org/2001/XMLSchema#double> .',
                '<https://ukfires.org/probs/ontology/data/simple/Object-Cake> <https://ukfires.org/probs/ontology/hasValue> "3"^^<http://www.w3.org/2001/XMLSchema#double> .',
            ]
        )

    # Now query the converted data
    query = "SELECT ?obj ?value WHERE { ?obj :hasValue ?value } ORDER BY ?obj"
    with probs_endpoint(
        output_filename, tmp_path / "working_reasoning", script_source_dir
    ) as rdfox:
        result = rdfox.query_records(query)

        assert result == [
            {"obj": NS["Object-Bread"], "value": 6.0},
            {"obj": NS["Object-Cake"], "value": 3.0},
        ]

        # Test answer_queries convenience function
        result2 = answer_queries(rdfox, {"q1": query})
        assert result2["q1"] == result