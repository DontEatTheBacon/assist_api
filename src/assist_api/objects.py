from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class Conjunction(Enum):
    AND = "And"
    OR = "Or"


@dataclass(frozen=True)
class AcademicYear:
    id: int
    fall_year: int


@dataclass(frozen=True)
class Institution:
    id: int
    name: str
    code: str
    is_community_college: bool


@dataclass(frozen=True)
class Major:
    id: str
    label: str
    receiving_institution: Institution
    sending_institution: Institution
    academic_year: AcademicYear


@dataclass(frozen=True)
class Course:
    title: str
    prefix: str
    number: str
    min_units: int
    max_units: int

    def __lt__(self, other):
        return (self.prefix + self.number) < (other.prefix + other.number)

    @classmethod
    def from_json(cls, data) -> Optional[Course]:
        title = data.get("courseTitle")
        prefix = data.get("prefix")
        number = data.get("courseNumber")
        min_units = data.get("minUnits")
        max_units = data.get("maxUnits")

        if (
            title is not None
            and prefix is not None
            and number is not None
            and min_units is not None
            and max_units is not None
        ):
            return cls(title, prefix, number, min_units, max_units)

        return None


@dataclass(frozen=True)
class Requirement:
    name: str


@dataclass(frozen=True)
class Series:
    conjunction: Conjunction
    items: tuple[Course | Series, ...]

    def __iter__(self):
        return iter(self.items)


@dataclass(frozen=True)
class Articulation:
    receiving: Course | Series | Requirement
    sending: Optional[Course | Series]


@dataclass(frozen=True)
class Section:
    articulations: tuple[Articulation, ...]

    def __iter__(self):
        return iter(self.articulations)


@dataclass(frozen=True)
class Group:
    instruction: dict[str, Any]
    sections: tuple[Section, ...]

    def __iter__(self):
        return iter(self.sections)


@dataclass(frozen=True)
class Agreement:
    groups: tuple[Group, ...]

    def __iter__(self):
        return iter(self.groups)