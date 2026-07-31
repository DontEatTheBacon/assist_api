from assist_api.client import AssistAPI
import json

with AssistAPI() as api:
    agreement = api.get_agreement('San Joaquin Delta College', 'To: University of California, San Diego', 'CSE: Computer Science B.S.')
    print(json.dumps(agreement.to_json()))

    # programs = api.get_programs('San Joaquin Delta College', 'To: University of California, Berkeley')
    # for program in programs:
    #     print(program)