# -*- coding: utf-8 -*-

from pathlib import Path
import gzip

from rdflib import Namespace, Graph, Literal, URIRef

from probs_runner import (
    PROBS, QUANTITYKIND,
    load_datasource,
    probs_endpoint,
    answer_queries,
    Observation,
)


NS = Namespace("https://ukfires.org/probs/ontology/data/simple/")


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
        output_filename, tmp_path / "working_reasoning", script_source_dir, port=12159
    ) as rdfox:
        result = rdfox.query_records(query)

        assert result == [
            {"obj": NS["Object-Bread"], "value": 6.0},
            {"obj": NS["Object-Cake"], "value": 3.0},
        ]

        # Test answer_queries convenience function
        result2 = answer_queries(rdfox, {"q1": query})
        assert result2["q1"] == result


def test_probs_endpoint_get_observations(tmp_path, script_source_dir):
    output_filename = tmp_path / "output.nt.gz"
    with gzip.open(output_filename, "wt") as f:
        f.write("""
<http://example.org/Obs> <https://ukfires.org/probs/ontology/measurement> "8551330"^^<http://www.w3.org/2001/XMLSchema#double> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/objectDefinedBy> <http://example.org/unfccc/N2O> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/processDefinedBy> <http://example.org/unfccc/1.> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://ukfires.org/probs/ontology/DirectObservation> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/prov#Entity> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://ukfires.org/probs/ontology/Observation> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/metric> <http://qudt.org/vocab/quantitykind/Mass> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/bound> <https://ukfires.org/probs/ontology/ExactBound> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/partOfDataset> <http://example.org/unfccc/UNFCCCData> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/objectDirectlyDefinedBy> <http://example.org/unfccc/N2O> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/processDirectlyDefinedBy> <http://example.org/unfccc/1.> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/hasRole> <https://ukfires.org/probs/ontology/ProcessOutput> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/hasTimePeriod> <https://ukfires.org/probs/ontology/TimePeriod_YearOf2018> .
<http://example.org/Obs> <https://ukfires.org/probs/ontology/hasRegion> <https://ukfires.org/probs/ontology/RegionGBR> .
        """)

    with probs_endpoint(
        output_filename, tmp_path, script_source_dir, port=12159
    ) as rdfox:
        result = rdfox.get_observations(
            time=PROBS.TimePeriod_YearOf2018,
            region=PROBS.RegionGBR,
            metric=QUANTITYKIND.Mass,
            role=PROBS.ProcessOutput,
            object_=URIRef("http://example.org/unfccc/N2O"),
            process=URIRef("http://example.org/unfccc/1."),
        )

        assert result == [
            Observation(
                uri=URIRef("http://example.org/Obs"),
                time=PROBS.TimePeriod_YearOf2018,
                region=PROBS.RegionGBR,
                metric=QUANTITYKIND.Mass,
                role=PROBS.ProcessOutput,
                object_=URIRef("http://example.org/unfccc/N2O"),
                process=URIRef("http://example.org/unfccc/1."),
                measurement=8551330,
                bound=PROBS.ExactBound,
            )
        ]

        result2 = rdfox.get_observations(
            time=PROBS.TimePeriod_YearOf2030,
            region=PROBS.RegionGBR,
            metric=QUANTITYKIND.Mass,
            role=PROBS.ProcessOutput,
            object_=URIRef("http://c-thru.org/data/external/unfccc/N2O"),
            process=URIRef("http://c-thru.org/data/external/unfccc/1."),
        )

        assert result2 == []
