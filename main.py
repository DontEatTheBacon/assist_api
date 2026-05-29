from assist_api.client import AssistAPI
import json

with AssistAPI() as api:
    agreement = api.get_agreement('San Joaquin Delta College', 'To: University of California, Berkeley', 'Physics, B.A.')
    print(json.dumps(agreement.to_json(), indent=4))