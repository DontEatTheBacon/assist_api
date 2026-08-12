# assist-api

A Python wrapper for the ASSIST.org articulation API.

## Installation

```
pip install assist-api
```

## Example

```python
from assist_api import AssistAPI

# Create API object
api = AssistAPI()

# Sending institution
sending_institution = api.get_institution_by_name('San Joaquin Delta College')
# Receiving institution
receiving_institution = api.get_institution_by_name('University of California, Santa Barbara')

# Academic year of agreement
academic_year = api.get_academic_year_by_fall_year(2025)

# Select major for agreement
comp_sci = next(
    (
        major 
        for major in api.get_majors(receiving_institution, sending_institution, academic_year) 
        if major.name == 'Computer Science, B.S.'
    ),
    None
)

# Returns an Agreement object
print(api.get_agreement(comp_sci))
```