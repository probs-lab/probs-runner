"""rdflib Namespace for PRObs."""

from rdflib import Namespace
from rdflib.namespace import RDF, RDFS


PROBS = Namespace("http://w3id.org/probs-lab/ontology#")
QUANTITYKIND = Namespace("http://qudt.org/vocab/quantitykind/")
PROV = Namespace("http://www.w3.org/ns/prov#")


NAMESPACES = {
    "": PROBS,
    "probs": PROBS,
    "rdf": RDF,
    "rdfs": RDFS,
    "prov": PROV,
    "quantitykind": QUANTITYKIND,
}
