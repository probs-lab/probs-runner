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
        SELECT ?obs ?measurement ?bound
        WHERE {
            ?obs a :Observation ;
                 :hasTimePeriod ?time ;
                 :hasRegion ?region ;
                 :metric ?metric ;
                 :hasRole ?role ;
                 %s
                 :bound ?bound .
            OPTIONAL { ?obs :measurement ?measurement . }
        }
    """


    def get_observations(self,
                         time: URIRef,
                         region: URIRef,
                         metric: URIRef,
                         role: URIRef,
                         object_: Optional[URIRef] = None,
                         process: Optional[URIRef] = None) -> List[Observation]:
        """Query for observations matching the given dimensions.

        :param time: value for `:hasTimePeriod`
        :param region: value for `:hasRegion`
        :param metric: value for `:metric`
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
        other = ""
        if object_ is not None:
            other += ":objectDefinedBy ?object ; "
            bindings["object"] = object_
        if process is not None:
            other += ":processDefinedBy ?process ; "
            bindings["process"] = process
        query = self.query_obs_template % other
        def _convert_measurement(value):
            return float(value) if value is not None else float("nan")
        return [
            Observation(
                uri=row["obs"],
                time=time,
                region=region,
                metric=metric,
                role=role,
                object_=object_,
                process=process,
                measurement=_convert_measurement(row["measurement"]),
                bound=row["bound"],
            )
            for row in self.query_records(query, initBindings=bindings)
        ]
