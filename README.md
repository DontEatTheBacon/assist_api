# assist-api

A python package that wraps assist.org's API.

## Installation

```
pip install assist-api
```

## Example

```python
# Create API object
api = AssistAPI()

# Get institution that is sending courses
sending_institution = api.get_institution_by_name('San Joaquin Delta College')
# Get institution that is receiving courses
receiving_institution = api.get_institution_by_name('University of California, Santa Barbara')

# Get year of agreement
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

print(api.get_agreement(comp_sci))
```