# assist-api

A Python wrapper for the ASSIST.org articulation API.

## Installation

```
pip install assist-api
```

## Quick Start

```python
from assist_api import AssistAPI

# Create API object
api = AssistAPI()

# Get institutions
sending_institution = api.get_institution_by_name('San Joaquin Delta College')
receiving_institution = api.get_institution_by_name('University of California, Santa Barbara')

# Select academic year
academic_year = api.get_academic_year_by_fall_year(2025)

# Find Computer Science major
comp_sci = next(
    (
        major 
        for major in api.get_majors(receiving_institution, sending_institution, academic_year) 
        if major.name == 'Computer Science, B.S.'
    ),
    None
)

if comp_sci is None:
    raise ValueError('Computer Science major not found')

# Fetch agreement
agreement = api.get_agreement(comp_sci)

print(agreement)
```