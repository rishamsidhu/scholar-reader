from dataclasses import dataclass

from common.types import SerializableEntity


@dataclass(frozen=True)
class Abbreviation(SerializableEntity):
    text: str

@dataclass(frozen=True)
class Expansion(SerializableEntity):
    text : str
    abb : str
    abb_locations : list
