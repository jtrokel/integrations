"""
Functions that interact with the kibana API
"""

import requests
import json

import constants

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


def br_create(config, group):
    headers = { 
        "Authorization": f"ApiKey {config['api_key']}",
        "Content-Type": "application/json",
        "kbn-xsrf": "exists"
    }

    hostname = group['hostname']

    body = {
        "policy_id": f"{group['policy_id']}",
        "package": {
            'name': 'httpjson',
            'version': '1.20.0',
        },
        "name": f"pcp-{hostname}-{group['interval']}",
        "description": f"Collect PCP metrics from {hostname} every {group['interval']}",
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
                            "request_url": f"{group['pmproxy_url']}pmapi/fetch?hostspec={hostname}.lle.rochester.edu&client={hostname}.lle.rochester.edu&names={group['metrics']}",
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
    
    return ('POST', f"{config['kibana_url']}api/fleet/package_policies", headers, body)


def br_view(config):
    pass


def br_delete(config):
    pass


def build_request(config, mode, group=None):
    if mode == constants.CREATE:
        return br_create(config, group)
    elif mode == constants.DELETE:
        return br_delete(config)
    elif mode == constants.VIEW:
        return br_view(config)
    else:
        print("what the")
        exit(1)


def request(req, args, mode):
    if mode == constants.CREATE:
        response = requests.request(req[0], req[1], headers=req[2], json=req[3])
    elif mode == constants.DELETE:
        pass
    elif mode == constants.VIEW:
        pass
    else:
        print("invalid mode")
        exit(1)

    if response.status_code == 409:
        print(response.text)
    
    if args.outfile:
        int_id = response.json()['item']['id']
        int_name = response.json()['item']['name']
        print(f"{int_name}: {int_id}")

