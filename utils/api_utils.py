"""Functions that interact with the kibana API.
"""

import sys

import requests

import constants

def validate_key(key, url):
    """Ensure api key and Kibana URL are valid."""
    resp = requests.get(f"{url}/api/fleet/agent_policies",
                        headers={"Authorization": f"ApiKey {key}"})

    if resp.status_code == 404:
        print("Could not reach kibana at the provided url:")
        print(resp.text)
        sys.exit(1)
    elif resp.status_code == 401:
        print("Could not validate with the provided API key:")
        print(resp.text)
        sys.exit(1)

    resp.raise_for_status()

    return True


def br_create(config, group):
    """Build HTTP request for the create command."""
    headers = {
        "Authorization": f"ApiKey {config['api_key']}",
        "Content-Type": "application/json",
        "kbn-xsrf": "exists"
    }

    fqdn = group['fqdn']
    hostname = fqdn[0:fqdn.find('.')]

    body = {
        "policy_id": f"{group['policy_id']}",
        "package": {
            'name': 'httpjson',
            'version': '1.20.0',
        },
        "name": f"pcp-{hostname}-{group['interval']}",
        "description": f"Collect PCP metrics from {fqdn} every {group['interval']}",
        "namespace": "default",
        "inputs": {
            "generic-httpjson": {
                "enabled": True,
                "streams": {
                    "httpjson.generic": {
                        "enabled": True,
                        "vars": {
                            "data_stream.dataset": "httpjson.pcp",
                            "pipeline": "pmwebapi-parser",
                            "request_url": f"{group['pmproxy_url']}/pmapi/fetch"
                                           "?hostspec={fqdn}"
                                           "&client={fqdn}"
                                           "&names={group['metrics']}",
                            "request_interval": f"{group['interval']}",
                            "request_method": "GET",
                            "request_redirect_headers_ban_list": [],
                            "oauth_scopes": [],
                            "tags": [
                                "forwarded"
                            ]
                        }
                    }
                }
            }
        }
    }

    return ('POST', f"{config['kibana_url']}/api/fleet/package_policies", headers, body)


def br_view(config):
    pass


def br_delete(config):
    pass


def build_request(config, mode, group=None):
    """Pass control to the request builder for the specified command."""
    if mode == constants.CREATE:
        return br_create(config, group)
    if mode == constants.DELETE:
        return br_delete(config)
    if mode == constants.VIEW:
        return br_view(config)

    print("what the")
    sys.exit(1)


def request(req, mode):
    """Send HTTP request with info from req."""
    if mode == constants.CREATE:
        response = requests.request(req[0], req[1], headers=req[2], json=req[3])
    elif mode == constants.DELETE:
        pass
    elif mode == constants.VIEW:
        pass
    else:
        print("invalid mode")
        sys.exit(1)

    if response.status_code == 409:
        print(response.text)
        return {}

    int_id = response.json()['item']['id']
    int_name = response.json()['item']['name']
    return {int_name: int_id}
