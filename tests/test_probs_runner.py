# -*- coding: utf-8 -*-

import shutil
from pathlib import Path
import gzip

from rdflib import Namespace, Graph, Literal

from probs_runner import (
    PROBS,
    load_datasource,
    probs_convert_data,
    probs_validate_data,
    probs_kbc_hierarchy,
    probs_enhance_data,
    probs_endpoint,
    answer_queries,
)


NS = Namespace("http://w3id.org/probs-lab/data/simple/")


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


def test_convert_data_ttl_from_dir(tmp_path, script_source_dir):
    # This directory has the data file and a load_data.rdfox script
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


def test_convert_data_ttl_directly(tmp_path, script_source_dir):
    # Also works by loading directly
    source = load_datasource(Path(__file__).parent / "sample_datasource_ttl" / "data.ttl")
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


def test_validate_data_ok(tmp_path, script_source_dir):
    source = load_datasource(Path(__file__).parent / "sample_datasource_ttl" / "data.ttl")
    result = probs_validate_data([source])
    assert result == True


def test_validate_data_not_ok(tmp_path, script_source_dir):
    original_filename = tmp_path / "original.nt.gz"
    with gzip.open(original_filename, "wt") as f:
        f.write(
            """
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#measurement> "8551330"^^<http://www.w3.org/2001/XMLSchema#double> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#objectDefinedBy> <http://example.org/unfccc/N2O> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#processDefinedBy> <http://example.org/unfccc/1.> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#DirectObservation> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/prov#Entity> .
<http://example.org/Obs> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#Observation> .
# Missing metric
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasBound> <http://w3id.org/probs-lab/ontology#ExactBound> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#partOfDataset> <http://example.org/unfccc/UNFCCCData> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#objectDirectlyDefinedBy> <http://example.org/unfccc/N2O> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#processDirectlyDefinedBy> <http://example.org/unfccc/1.> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasRole> <http://w3id.org/probs-lab/ontology#ProcessOutput> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasTime> <http://w3id.org/probs-lab/ontology#TimePeriod_YearOf2018> .
<http://example.org/Obs> <http://w3id.org/probs-lab/ontology#hasRegion> <http://w3id.org/probs-lab/ontology#RegionGBR> .
<http://example.org/unfccc/N2O_equiv> <http://w3id.org/probs-lab/ontology#objectEquivalentTo> <http://example.org/unfccc/N2O> .
        """
        )
    source = load_datasource(original_filename)
    result = probs_validate_data([source], debug_files=tmp_path/"debug_files")
    assert result == False

    assert len(list(tmp_path.rglob("debug_files/tests.csv"))) == 1
    assert len(list(tmp_path.rglob("debug_files/test_*"))) > 0


def test_enhance_data(tmp_path, script_source_dir):
    original_filename = tmp_path / "original.nt.gz"
    enhanced_filename = tmp_path / "enhanced.nt.gz"
    with gzip.open(original_filename, "wt") as f:
        f.write(
            """
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
<http://example.org/unfccc/N2O_equiv> <http://w3id.org/probs-lab/ontology#objectEquivalentTo> <http://example.org/unfccc/N2O> .
        """
        )

    probs_kbc_hierarchy(
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
<http://w3id.org/probs-lab/ontology/data/simple/{object_name}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://w3id.org/probs-lab/ontology#Object> .
"""
        )


def _setup_test_ttl_data(p, object_name):
    p.parent.mkdir(exist_ok=True, parents=True)
    with open(p, "wt") as f:
        f.write(
            f"""
@prefix simple: <http://w3id.org/probs-lab/ontology/data/simple/> .
@prefix probs: <http://w3id.org/probs-lab/ontology#> .
simple:{object_name} a probs:Object .
"""
        )


def test_enhance_data_string_path(tmp_path, script_source_dir):
    original_filename = tmp_path / "original.nt.gz"
    enhanced_filename = tmp_path / "enhanced.nt.gz"
    _setup_test_nt_gz_data(original_filename, "Object-Bread")

    probs_kbc_hierarchy(
        str(original_filename),
        enhanced_filename,
        tmp_path / "working_enhanced",
        script_source_dir,
    )
