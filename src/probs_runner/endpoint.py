""" Custom subclass of RDFoxEndpoint with additional query functions.

"""

from dataclasses import dataclass
from typing import Optional, List

from rdflib import URIRef
from rdfox_runner import RDFoxEndpoint

from .namespace import PROBS


@dataclass
class Observation:
    """A PRObs Observation."""

    uri: URIRef
    time: URIRef
    region: URIRef
    metric: URIRef
    role: URIRef
    object_: Optional[URIRef] = None
    process: Optional[URIRef] = None
    measurement: Optional[float] = None
    bound: URIRef = PROBS.ExactBound


class PRObsEndpoint(RDFoxEndpoint):
    """Subclass of RDFoxEndpoint with additional query functions.

    """

    query_obs_template = """
        SELECT ?obs ?measurement ?bound ?process ?object
        WHERE {
            ?obs a :Observation ;
                 :hasTime ?time ;
                 :hasRegion ?region ;
                 :hasMetric ?metric ;
                 :hasRole ?role ;
                 %s
                 :hasBound ?bound .
                 %s    
            OPTIONAL { ?obs :measurement ?measurement . }
        }
    """

    def get_observations(self,
                         time: URIRef,
                         region: URIRef,
                         metric: URIRef,
                         role: URIRef,
                         object_: Optional[URIRef] = None,
                         process: Optional[URIRef] = None,
                         object_code: Optional[str] = None,
                         process_code: Optional[str] = None) -> List[Observation]:

        """Query for observations matching the given dimensions.

        :param time: value for `:hasTime`
        :param region: value for `:hasRegion`
        :param metric: value for `:hasMetric`
        :param role: value for `:hasRole`
        :param object\\_: value for `:objectDefinedBy` (optional, depending on `role`)
        :param process: value for `:processDefinedBy` (optional, depending on `role`)

        :returns: list of :py:class:`Observation` objects

        """
        bindings = {
            "time": time,
            "region": region,
            "metric": metric,
            "role": role
        }
        other1 = ""
        other2 = ""
        if object_ is not None:
            other1 += ":objectDefinedBy ?object ;"
            bindings["object"] = object_
        elif object_code is not None:
            other1 += """
                 :objectDefinedBy ?object;""" 
            other2 += """
            ?object :hasClassificationCode ?code .
            ?code rdfs:label ?cname .
            FILTER (STR(?cname) = %s)""" % ("\"" + object_code + "\"")
        else:
            other2 += """
            OPTIONAL { ?obs :objectDefinedBy ?object . }"""
        if process is not None:
            other1 += """
                 :processDefinedBy ?process ;"""
            bindings["process"] = process
        elif process_code is not None:
            other1 += """
                 :processDefinedBy ?process ;"""
            other2 += """
            ?process rdfs:label ?code .
            FILTER (STR(?code) = %s)""" % ("\"" + process_code + "\"")
        else:
            other2 += """
            OPTIONAL { ?obs :processDefinedBy ?process . }"""
        query = self.query_obs_template % (other1, other2)
        def _convert_measurement(value):
            return float(value) if value is not None else float("nan")
        results = []
        for row in self.query_records(query, initBindings=bindings):
            if object == None and object_code == None:
                return_object = None
            else:
                return_object = row["object"]
            if process == None and process_code == None:
                return_process = None
            else:
                return_process = row["process"]
            results.append(
                Observation(
                    uri=row["obs"],
                    time=time,
                    region=region,
                    metric=metric,
                    role=role,
                    object_=return_object,
                    process=return_process,
                    measurement=_convert_measurement(row["measurement"]),
                    bound=row["bound"],
                )
            )
        return results 
