"""Functions that interact with the kibana API.
"""

from collections import defaultdict
import json
import re
import sys

import requests

import constants


def validate_key(key, url):
    """Ensure api key and Kibana URL are valid."""
    resp = requests.get(
        f"{url}/api/fleet/agent_policies",
        headers={"Authorization": f"ApiKey {key}"},
        timeout=10,
    )

    if resp.status_code == 404:
        print("Could not reach kibana at the provided url:", file=sys.stderr)
        print(resp.text)
        sys.exit(1)
    elif resp.status_code == 401:
        print("Could not validate with the provided API key:", file=sys.stderr)
        print(resp.text)
        sys.exit(1)

    resp.raise_for_status()

    return True


def generate_map(key, url, extended=False):
    """Create an integration name->id map from the Kibana API."""
    idmap = defaultdict(dict)
    resp = requests.get(
        f"{url}/api/fleet/package_policies",
        headers={"Authorization": f"ApiKey {key}", "kbn-xsrf": "true"},
        timeout=10,
    )
    resp_body = resp.json()

    for integration in resp_body["items"]:
        name = integration["name"]
        id_ = integration["id"]
        if not re.match(r"^\.pcp-", name):
            continue

        idmap[name]["id"] = id_
        if extended:
            idmap[name] = integration
            idmap[name]["enabled_"] = (
                integration["inputs"][0]["enabled"]
                and integration["inputs"][0]["streams"][0]["enabled"]
            )
            url = re.match(
                r"^http:\/\/(.*?)\/pmapi\/fetch\?hostspec=(.*?)&.*&names=(.*)$",
                integration["inputs"][0]["streams"][0]["vars"]["request_url"]["value"],
            )
            idmap[name]["pmproxy_url_"] = url.group(1)
            idmap[name]["metrics_"] = url.group(3)
            idmap[name]["hostname_"] = url.group(2)

    return idmap


def br_create(config, group):
    """Build HTTP request for the create command."""
    headers = {
        "Authorization": f"ApiKey {config['api_key']}",
        "Content-Type": "application/json",
        "kbn-xsrf": "exists",
    }

    fqdn = group["fqdn"]
    hostname = fqdn[0 : fqdn.find(".")]

    body = {
        "policy_id": f"{group['policy_id']}",
        "package": {
            "name": "httpjson",
            "version": "1.20.0",
        },
        "name": f".pcp-{hostname}-{group['interval']}",
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
                            f"?hostspec={fqdn}"
                            f"&client={fqdn}"
                            f"&names={group['metrics']}",
                            "request_interval": f"{group['interval']}",
                            "request_method": "GET",
                            "request_redirect_headers_ban_list": [],
                            "oauth_scopes": [],
                            "tags": ["forwarded"],
                        },
                    }
                },
            }
        },
    }

    return ("POST", f"{config['kibana_url']}/api/fleet/package_policies", headers, body)


def br_list(config):
    """Build HTTP request for the list command."""
    pass


def br_delete(config, id_):
    """Build HTTP request for the delete command."""
    method = "DELETE"
    url = f"{config['kibana_url']}/api/fleet/package_policies/{id_}"
    headers = {"Authorization": f"ApiKey {config['api_key']}", "kbn-xsrf": "exists"}
    return (method, url, headers)


def br_update(config, id_):
    """Build HTTP request for the update command."""
    method = "PUT"
    url = f"{config['kibana_url']}/api/fleet/package_policies/{id_}"
    headers = {"Authorization": f"ApiKey {config['api_key']}", "kbn-xsrf": "exists"}

    url_re = re.compile(r"^.*?(/p.*?spec=).*?(&client=).*?(&names=).*$")
    for inp in config["inputs"]:
        for stream in config["inputs"][inp]["streams"]:
            old_url = config["inputs"][inp]["streams"][stream]["vars"]["request_url"]
            transformed_url = url_re.sub(
                config["pmproxy_url_"]
                + r"\2"
                + config["hostname_"]
                + r"\3"
                + config["hostname_"]
                + r"\4"
                + config["metrics_"],
                old_url,
            )
            config["inputs"][inp]["streams"][stream]["vars"][
                "request_url"
            ] = transformed_url

    del config["kibana_url"]
    del config["api_key"]
    del config["pmproxy_url_"]
    del config["hostname_"]
    del config["metrics_"]

    return (method, url, headers, config)


def build_request(config, mode, group=None, id_=None):
    """Pass control to the request builder for the specified command."""
    if mode == constants.CREATE:
        return br_create(config, group)
    if mode == constants.DELETE:
        return br_delete(config, id_)
    if mode == constants.LIST:
        return br_list(config)
    if mode == constants.UPDATE:
        return br_update(config, id_)

    print("what the")
    sys.exit(1)


def request(req, mode):
    """Send HTTP request with info from req."""
    if mode == constants.CREATE:
        response = requests.request(
            req[0], req[1], headers=req[2], json=req[3], timeout=10
        )
        if response.status_code == 409:
            print(response.text)
            return {}

        int_id = response.json()["item"]["id"]
        int_name = response.json()["item"]["name"]
        return {int_name: int_id}

    if mode == constants.DELETE:
        response = requests.request(req[0], req[1], headers=req[2], timeout=10)
        if response.status_code != 200:
            print(response.text)
        return {}

    if mode == constants.LIST:
        pass

    if mode == constants.UPDATE:
        response = requests.request(
            req[0], req[1], headers=req[2], json=json.dumps(req[3]), timeout=10
        )
        # Handled in caller
        response.raise_for_status()
        return {}

    print("invalid mode", file=sys.stderr)
    sys.exit(1)
