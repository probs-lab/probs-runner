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


NS = Namespace("http://w3id.org/probs-lab/ontology/data/simple/")

def test_probs_endpoint(tmp_path, script_source_dir):
    output_filename = tmp_path / "output.nt.gz"
    with gzip.open(output_filename, "wt") as f:
        f.writelines(
            [
                '<http://w3id.org/probs-lab/ontology/data/simple/Object-Bread> <http://w3id.org/probs-lab/ontology#hasValue> "6"^^<http://www.w3.org/2001/XMLSchema#double> .',
                '<http://w3id.org/probs-lab/ontology/data/simple/Object-Cake> <http://w3id.org/probs-lab/ontology#hasValue> "3"^^<http://www.w3.org/2001/XMLSchema#double> .',
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
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#measurement> "8551330"^^<http://www.w3.org/2001/XMLSchema#double> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#objectDefinedBy> <http://example.org/unfccc/N2O> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#processDefinedBy> <http://example.org/unfccc/1.> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#DirectObservation> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/prov#Entity> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#Observation> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasMetric> <http://qudt.org/vocab/quantitykind/Mass> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasBound> <http://w3id.org/probs-lab/ontology#ExactBound> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#partOfDataset> <http://example.org/unfccc/UNFCCCData> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#objectDirectlyDefinedBy> <http://example.org/unfccc/N2O> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#processDirectlyDefinedBy> <http://example.org/unfccc/1.> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasRole> <http://w3id.org/probs-lab/ontology#ProcessOutput> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasTime> <http://w3id.org/probs-lab/ontology#TimePeriod_YearOf2018> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasRegion> <http://w3id.org/probs-lab/ontology#RegionGBR> .
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


def test_probs_endpoint_get_observations_by_process_code(tmp_path, script_source_dir):
    output_filename = tmp_path / "output.nt.gz"
    with gzip.open(output_filename, "wt") as f:
        f.write("""
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#measurement> "8551330"^^<http://www.w3.org/2001/XMLSchema#double> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#objectDefinedBy> <http://example.org/unfccc/N2O> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#processDefinedBy> <http://example.org/unfccc/1.> .
<http://example.org/unfccc/1.> <http://www.w3.org/2000/01/rdf-schema#label> "1.  Energy>" .
<http://example.org/unfccc/1.> <http://www.w3.org/2000/01/rdf-schema#label> "1_with_LULUCF" .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#DirectObservation> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/prov#Entity> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#Observation> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasMetric> <http://qudt.org/vocab/quantitykind/Mass> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasBound> <http://w3id.org/probs-lab/ontology#ExactBound> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#partOfDataset> <http://example.org/unfccc/UNFCCCData> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#objectDirectlyDefinedBy> <http://example.org/unfccc/N2O> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#processDirectlyDefinedBy> <http://example.org/unfccc/1.> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasRole> <http://w3id.org/probs-lab/ontology#ProcessOutput> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasTime> <http://w3id.org/probs-lab/ontology#TimePeriod_YearOf2018> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasRegion> <http://w3id.org/probs-lab/ontology#RegionGBR> .
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
            process_code= "1_with_LULUCF",
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
            time=PROBS.TimePeriod_YearOf2018,
            region=PROBS.RegionGBR,
            metric=QUANTITYKIND.Mass,
            role=PROBS.ProcessOutput,
            object_=URIRef("http://example.org/unfccc/N2O"),
            process_code="2_with_LULUCF",
        )

        assert result2 == []



def test_probs_endpoint_get_observations_by_object_code(tmp_path, script_source_dir):
    output_filename = tmp_path / "output.nt.gz"
    with gzip.open(output_filename, "wt") as f:
        f.write("""
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#measurement> "8551330"^^<http://www.w3.org/2001/XMLSchema#double> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#objectDefinedBy> <http://example.org/prodcom/Object-1234> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#DirectObservation> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/prov#Entity> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#Observation> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasMetric> <http://qudt.org/vocab/quantitykind/Mass> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasBound> <http://w3id.org/probs-lab/ontology#ExactBound> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#partOfDataset> <http://example.org/prodcom/PRODCOM2016DATA> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#objectDirectlyDefinedBy> <http://example.org/prodcom/Object-1234> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasRole> <http://w3id.org/probs-lab/ontology#SoldProduction> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasTime> <http://w3id.org/probs-lab/ontology#TimePeriod_YearOf2016> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasRegion> <http://w3id.org/probs-lab/ontology#RegionGBR> .
<http://example.org/prodcom/Object-1234> <http://w3id.org/probs-lab/ontology#hasClassificationCode> <http://example.org/prodcom/2016/ClassificationCode-1234> .
<http://example.org/prodcom/Object-1234> <http://www.w3.org/2000/01/rdf-schema#label> "PRODCOM Object corresponding to Code 1234" .
<http://example.org/prodcom/2016/ClassificationCode-1234> <http://w3id.org/probs-lab/ontology#codeDescription> "An test PRODCOM commodity" .
<http://example.org/prodcom/2016/ClassificationCode-1234> <http://www.w3.org/2000/01/rdf-schema#label> "1234" .
<http://example.org/prodcom/2016/ClassificationCode-1234> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/prodcom/ClassificationCode> .
        """)


    with probs_endpoint(
        output_filename, tmp_path, script_source_dir, port=12159
    ) as rdfox:
        result = rdfox.get_observations(
            time=PROBS.TimePeriod_YearOf2016,
            region=PROBS.RegionGBR,
            metric=QUANTITYKIND.Mass,
            role=PROBS.SoldProduction,
            object_code="1234",
        )

        assert result == [
            Observation(
                uri=URIRef("http://example.org/Obs"),
                time=PROBS.TimePeriod_YearOf2016,
                region=PROBS.RegionGBR,
                metric=QUANTITYKIND.Mass,
                role=PROBS.SoldProduction,
                object_=URIRef("http://example.org/prodcom/Object-1234"),
                measurement=8551330,
                bound=PROBS.ExactBound,
            )
        ]

        result2 = rdfox.get_observations(
            time=PROBS.TimePeriod_YearOf2016,
            region=PROBS.RegionGBR,
            metric=QUANTITYKIND.Mass,
            role=PROBS.SoldProduction,
            object_code="2345",
        )

        assert result2 == []



