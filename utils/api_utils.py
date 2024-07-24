"""
Functions that interact with the kibana API
"""

import requests

def validate_key(key, url):
    r = requests.get(f"{url}api/fleet/agent_policies", headers={"Authorization": f"ApiKey {key}"})

    if r.status_code == 404:
        print("Could not reach kibana at the provided url:")
        print(r.text)
        sys.exit(1)
    elif r.status_code == 401:
        print("Could not validate with the provided API key:")
        print(r.text)
        sys.exit(1)

    r.raise_for_status()

    return True


