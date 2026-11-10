"""EgoSpatial: a portable spatial reasoning engine for XR.

Deterministic geometry (exact, dependency-free) + optional neural semantic parsing.
"""
from .frames import (bearing_degrees, displacement, egocentric_to_world, normalize_heading,
                     world_to_egocentric)
from .state import SpatialObject, SpatialState, SpatialStateError
from .relations import (DIRECTIONS, all_relations, classify_egocentric_direction, distance, object_to_agent,
                        object_to_object, reference_frame)
from .query import Query, template_parse
from .orchestrator import SpatialEngine
from . import adapters

__version__ = "1.0.1"
__all__ = [
    "SpatialState", "SpatialObject", "SpatialStateError", "SpatialEngine", "Query", "template_parse",
    "object_to_agent", "object_to_object", "reference_frame", "distance", "all_relations",
    "classify_egocentric_direction", "world_to_egocentric", "egocentric_to_world", "bearing_degrees",
    "displacement", "normalize_heading", "DIRECTIONS", "adapters", "__version__",
]
