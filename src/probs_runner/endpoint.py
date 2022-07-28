""" Custom subclass of RDFoxEndpoint with additional query functions.

"""

from typing import Optional, List, Tuple
from rdflib import URIRef
from rdfox_runner import RDFoxEndpoint
from .namespace import PROBS


class PRObsEndpoint(RDFoxEndpoint):
    """Subclass of RDFoxEndpoint with additional query functions.

    """

    query_obs_template = """
        SELECT ?measurement ?bound
        WHERE {
            ?obs a :Observation ;
                 :hasTimePeriod ?time ;
                 :hasRegion ?region ;
                 :metric ?metric ;
                 :hasRole ?role ;
                 %s
                 :measurement ?measurement ;
                 :bound ?bound .
        }
    """


    def get_observations(self,
                         time: URIRef,
                         region: URIRef,
                         metric: URIRef,
                         role: URIRef,
                         object_: Optional[URIRef] = None,
                         process: Optional[URIRef] = None) -> List[Tuple[str, float]]:
        """Query for observations matching the given dimensions.

        :param time: value for `:hasTimePeriod`
        :param region: value for `:hasRegion`
        :param metric: value for `:metric`
        :param role: value for `:hasRole`
        :param object\\_: value for `:objectDefinedBy` (optional, depending on `role`)
        :param process: value for `:processDefinedBy` (optional, depending on `role`)

        :returns: list of (`bound`, `measurement`) tuples, where `bound` is
                  either ``"="`` or ``">"`` for an exact or lower bound respectively.

        """
        bindings = {
            "time": time,
            "region": region,
            "metric": metric,
            "role": role
        }
        other = ""
        if object_ is not None:
            other += ":objectDefinedBy ?object ; "
            bindings["object"] = object_
        if process is not None:
            other += ":processDefinedBy ?process ; "
            bindings["process"] = process
        query = self.query_obs_template % other
        bound_strings = {
            PROBS.LowerBound: ">",
            PROBS.ExactBound: "=",
        }
        return [
            (bound_strings[row["bound"]], float(row["measurement"]))
            for row in self.query_records(query, initBindings=bindings)
        ]
