from enum import Enum
from typing import List, Optional
from bs4 import Tag
import re

class CSSClasses:
    GROUP = 'group'
    GROUP_NUMBER = 'groupNumber'
    GROUP_HEADER = 'instructionsHeader'
    SECTION = 'sectionMain'
    SECTION_LETTER = 'sectionLetter'
    ROW = 'articRow'
    RECEIVING = 'rowReceiving'
    SENDING = 'view_sending__content'
    OR_ROOT = 'conjunction or standAlone'
    OR_SERIES = 'conjunction or series'
    AND_ROOT = 'and conjunction standAlone'
    AND_SERIES = 'and conjunction series'
    COURSE = 'courseLine'
    COURSE_NUMBER = 'prefixCourseNumber'
    COURSE_TITLE = 'courseTitle'
    COURSE_UNITS = 'courseUnits'
    SERIES = 'bracketWrapper'
    SERIES_CONTENT = 'bracketContent'

class ClauseType(Enum):
    AND = 'AND'
    OR = 'OR'

class Course:
    def __init__(self, number: str, title: str, units: float):
        # consider different names?
        self.number: str = number
        self.title: str = title
        self.units: float = units

    def __repr__(self) -> str:
        return f'<Course {self.number}>'

    @classmethod
    def from_element(cls: Course, element: Tag):
        course_units = element.find(class_=CSSClasses.COURSE_UNITS)
        match = None

        if course_units:
            match = re.search(r'[0-9]*\.[0-9]*', course_units.get_text())

        return cls(
            element.find(class_=CSSClasses.COURSE_NUMBER).get_text().strip(),
            element.find(class_=CSSClasses.COURSE_TITLE).get_text().strip(),
            float(match.group(0)) if match else 0.0
        )

    def to_json(self) -> dict:
        return {
            'type': 'COURSE',
            'data': {
                'number': self.number,
                'title': self.title,
                'units': self.units
            }
        }

class Series:
    def __init__(self, clause: ClauseType, children: List[Course | Series]):
        self.clause: ClauseType = clause
        self.children: List[Course | Series] = children

    def __repr__(self):
        return f'<Series {self.clause.value} [{', '.join([str(child) for child in self.children])}]>'

    @classmethod
    def from_element(cls: Series, element: Tag, children: List[Course | Series]):
        clause = None

        if element.find(class_=CSSClasses.AND_SERIES):
            clause = ClauseType.AND
        elif element.find(class_=CSSClasses.OR_SERIES):
            clause = ClauseType.OR

        return cls(
            clause,
            children
        )

    def to_json(self) -> dict:
        # children may be either Series or Course objects
        data = [child.to_json() for child in self.children]

        return {
            'type': self.clause.value,
            'data': data
        }

class Row:
    def __init__(self, receiving: Course | Series, sending: Course | Series):
        self.receiving = receiving
        self.sending = sending

    def __repr__(self):
        return f'<Row {self.sending} -> {self.receiving}>'
    
    def to_json(self):
        return {
            'receiving': self.receiving.to_json() if self.receiving else { 'type': 'NONE' },
            'sending': self.sending.to_json() if self.sending else { 'type': 'NONE' }
        }
    
class Section:
    def __init__(self, letter: Optional[str], rows: List[Row]):
        self.letter: Optional[str] = letter
        self.rows: List[Row] = rows

    def __repr__(self):
        return f'<Section {self.letter}>'
    
    def to_json(self):
        return {
            'letter': self.letter,
            'rows': [row.to_json() for row in self.rows]
        }

class Group:
    def __init__(self, number: int, header: str, sections: List[Section]):
        self.number: int = number
        self.header: str = header
        self.sections: List[Section] = sections

    def __repr__(self):
        return f'<Group {self.number}>'
    
    def to_json(self):
        return {
            'number': self.number,
            'header': self.header,
            'sections': [section.to_json() for section in self.sections]
        }
    
class Agreement:
    def __init__(self, groups: List[Group]):
        self.groups: List[Group] = groups

    def to_json(self):
        return [group.to_json() for group in self.groups]
    
    def rows(self) -> List[Row]:
        rows = []

        for group in self.groups:
            for section in group.sections:
                for row in section.rows:
                    rows.append(row)

        return rows
    
    def articulated_rows(self) -> List[Row]:
        rows = []

        for row in self.rows():
            if row.receiving and row.sending:
                rows.append(row)

        return rows
    
    def missing_rows(self) -> List[Row]:
        rows = []

        for row in self.rows():
            if row.receiving and not row.sending:
                rows.append(row)

        return rows
    
    def sections(self) -> List[Section]:
        sections = []

        for group in self.groups:
            for section in group.sections:
                sections.append(section)

        return sections