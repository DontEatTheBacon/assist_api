# assist-api

A python package that wraps assist.org's API.

## Installation

```
pip install assist-api
```

## Example

```python
api = AssistAPI()

sending_institution = api.get_institution_by_name('San Joaquin Delta College')
receiving_institution = api.get_institution_by_name('University of California, Santa Barbara')

academic_year = api.get_academic_year_by_fall_year(2025)

comp_sci = next(
    (major for major in api.get_majors() if major.name == 'Computer Science, B.S.'),
    None
)

print(api.get_agreement(comp_sci))
```