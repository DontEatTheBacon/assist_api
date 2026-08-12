import json
import requests
from typing import Optional

from .objects import (
    AcademicYear, 
    Agreement, 
    Articulation, 
    Conjunction, 
    Course, 
    Group,
    Institution, 
    Major, 
    Requirement, 
    Section,
    Series,
)

class AssistAPI:

    def __init__(self):
        self._session = requests.Session()
        self._session.get('https://assist.org')

    @property
    def headers(self):
        return {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'X-XSRF-TOKEN': self._session.cookies['X-XSRF-TOKEN'],
            'User-Agent': 'Mozilla/5.0'
        }

    def get_academic_years(self) -> list[AcademicYear]:
        URL = 'https://assist.org/api/academicyears'

        request = self._session.get(URL, headers=self.headers)
        request.raise_for_status()

        data = request.json()

        years = []
        for year in data:
            id = year.get('id')
            fall_year = year.get('fallYear')

            if id is not None and fall_year is not None:
                years.append(AcademicYear(id, fall_year))

        return years

    def get_academic_year_by_fall_year(self, fall_year: int) -> Optional[AcademicYear]:
        academic_years = self.get_academic_years()

        return next(
            (academic_year for academic_year in academic_years if academic_year.fall_year == fall_year),
            None
        )
        
    def get_institutions(self) -> list[Institution]:
        URL = 'https://assist.org/api/institutions'

        request = self._session.get(URL, headers=self.headers)
        request.raise_for_status()

        data = request.json()

        institutions = []
        for institution in data:
            id = institution.get('id')

            names = institution.get('names', [])
            if names:
                name = institution.get('names')[0].get('name')

            code = institution.get('code')
            is_community_college = institution.get('isCommunityCollege')

            if id is not None and name is not None and code is not None and is_community_college is not None:
                institutions.append(Institution(id, name, code, is_community_college))

        return institutions

    def get_institution_by_name(self, name: str) -> Optional[Institution]:
        institutions = self.get_institutions()

        return next(
            (institution for institution in institutions if institution.name == name),
            None
        )
    
    def get_majors(
            self,
            receiving_institution: Institution, 
            sending_institution: Institution, 
            academic_year: AcademicYear
        ) -> list[Major]:

        URL = 'https://assist.org/api/agreements'

        params = {
            'receivingInstitutionId': receiving_institution.id,
            'sendingInstitutionId': sending_institution.id,
            'academicYearId': academic_year.id,
            'categoryCode': 'major'
        }

        request = self._session.get(
            URL, 
            headers=self.headers, 
            params=params
        )

        request.raise_for_status()
        data = request.json()

        majors = []
        for item in data.get('reports', []):
            label = item.get('label')
            key = item.get('key')

            if label is not None and key is not None:
                majors.append(
                    Major(
                        key, 
                        label, 
                        receiving_institution, 
                        sending_institution, 
                        academic_year
                    )
                )

        return majors

    def _map_articulations(self, data):
        # get mapping for articulations
        mapping = {}

        # json for articulations
        rows = json.loads(data['articulations']) 

        for row in rows:
            receiving = None
            sending = None

            articulation_data = row['articulation']

            # get receiving course
            receiving_type = articulation_data['type']

            if receiving_type == 'Course':
                receiving = Course.from_json(articulation_data['course'])

            elif receiving_type == 'Series':
                series = articulation_data['series']
                conjunction = series['conjunction']
                courses = []

                for course in series['courses']:
                    courses.append(Course.from_json(course))

                receiving = Series(Conjunction(conjunction), tuple(courses))

            elif receiving_type == 'Requirement':
                name = articulation_data['requirement']['name']
                receiving = Requirement(name)

            else:
                # Unrecognized type
                raise NotImplementedError

            # get sending course(s)
            sending_data = articulation_data['sendingArticulation']

            # courses / nested series
            items = sending_data['items']

            if len(items) > 1:
                # conjunction for root
                root_conjunction = sending_data['courseGroupConjunctions'][0]['groupConjunction'] if len(sending_data['courseGroupConjunctions']) > 0 else None
                series_items = []

                for item in items:
                    conjunction = item['courseConjunction']
                    subitems = item['items']

                    if len(subitems) > 1:
                        courses = []

                        for subitem in subitems:
                            courses.append(Course.from_json(subitem))

                        series_items.append(Series(
                            Conjunction(conjunction),
                            tuple(sorted(courses))
                        ))
                    else:
                        series_items.append(
                            Course.from_json(subitems[0])
                        )

                sending = Series(
                    Conjunction(root_conjunction),
                    tuple(series_items)
                )
                
            elif items:
                conjunction = items[0]['courseConjunction']
                subitems = items[0]['items']

                # standalone series
                if len(subitems) > 1:
                    courses = []

                    for subitem in subitems:
                        courses.append(Course.from_json(subitem))

                    sending = Series(
                        Conjunction(conjunction),
                        tuple(sorted(courses))
                    )

                # stand-alone course
                else:
                    sending = Course.from_json(subitems[0])

            else:
                # empty items???
                # Occurs on never articulated courses as far as I know
                
                # Should be a string if not articulated
                if sending_data.get('noArticulationReason') is None:
                    raise NotImplementedError

            if receiving:
                mapping[receiving] = sending

        return mapping

    def get_agreement(self, major: Major):
        # agreements before 2023 are .pdf files
        if major.academic_year.fall_year < 2023:
            raise NotImplementedError

        URL = 'https://assist.org/api/articulation/Agreements'

        params = {
            'Key': f'{major.id}'
        }

        request = self._session.get(URL, params=params, headers=self.headers)
        request.raise_for_status()

        data = request.json()
        result = data['result']

        # get mapping for articulations
        mapping = self._map_articulations(result)

        assets = json.loads(result['templateAssets'])
        groups = []

        # template assets: included groups and text
        for asset in assets:
            asset_type = asset['type']

            if asset_type == 'RequirementGroup':
                # instruction
                instruction = asset['instruction']
                group_id = asset['groupId']

                # handle sections
                section_data = asset['sections']
                sections = []

                for section in section_data:
                    articulations = []

                    # each row is an articulation 
                    rows = section['rows']
                    for row in rows:
                        cells = row['cells']

                        # course for each row on receiving side
                        for cell in cells:
                            cell_type = cell['type']

                            if cell_type == 'Course':
                                course = Course.from_json(cell['course'])

                                articulations.append(
                                    Articulation(
                                        course,
                                        mapping.get(course)
                                    )
                                )

                            elif cell_type == 'Requirement':
                                name = cell['requirement']['name']
                                requirement = Requirement(name)

                                articulations.append(
                                    Articulation(
                                        requirement,
                                        mapping.get(requirement)
                                    )
                                )
                                
                            elif cell_type == 'Series':
                                series_data = cell['series']
                                conjunction = series_data['conjunction']
                                courses = []

                                for course in series_data['courses']:
                                    courses.append(Course.from_json(course))

                                series = Series(Conjunction(conjunction), tuple(sorted(courses)))

                                articulations.append(
                                    Articulation(
                                        series,
                                        mapping.get(series)
                                    )
                                )

                            else:
                                # Unrecognized type
                                raise NotImplementedError

                    sections.append(
                        Section(
                            tuple(articulations)
                        )
                    )

                groups.append(Group(
                    instruction,
                    tuple(sections)
                ))

            elif asset_type == 'GeneralText' or asset_type == 'GeneralTitle' or asset_type == 'RequirementTitle':
                # Text elements that are bound to a group
                pass

            else:
                # Unrecognized elements
                raise NotImplementedError

        return Agreement(tuple(groups))

    def get_receiving_agreements(self, institution: Institution) -> dict[Institution, list[AcademicYear]]:
        URL = f'https://assist.org/api/institutions/{institution.id}/agreements?asSendingOnly=true'

        request = self._session.get(URL, headers=self.headers)
        result = request.json()

        institution_mapping = {}
        year_mapping = {}

        agreements = {}

        for school in self.get_institutions():
            institution_mapping[school.id] = school

        for year in self.get_academic_years():
            year_mapping[year.id] = year

        for item in result:
            agreements[institution_mapping[item['institutionParentId']]] = [year_mapping[year_id] for year_id in item['receivingYearIds']]

        return agreements

    def get_sending_agreements(self, institution: Institution) -> dict[Institution, list[AcademicYear]]:
        URL = f'https://assist.org/api/institutions/{institution.id}/agreements?asSendingOnly=true'

        request = self._session.get(URL, headers=self.headers)
        result = request.json()

        institution_mapping = {}
        year_mapping = {}

        agreements = {}

        for school in self.get_institutions():
            institution_mapping[school.id] = school

        for year in self.get_academic_years():
            year_mapping[year.id] = year

        for item in result:
            agreements[institution_mapping[item['institutionParentId']]] = [year_mapping[year_id] for year_id in item['sendingYearIds']]

        return agreements
