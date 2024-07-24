#!/usr/bin/env python3

import json
import requests
import argparse
import sys

from utils import api_utils
from modes import create, view, delete 


def create_integrations(node, key, url):
    hostname = node['hostname']
    
    for group in node['groups']:
        headers = { 
            "Authorization": f"ApiKey {key}",
            "Content-Type": "application/json",
            "kbn-xsrf": "exists"
        }

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

        print("Sending request")
        response = requests.post(f"{url}api/fleet/package_policies", headers=headers, json=body)
        
        if response.status_code == 409:
            print(response.text)


def build_parser():
    parser = argparse.ArgumentParser("integrations")
    parser.add_argument('--check-config', action='store_true', help="Validate the structure of the config file passed to -f and do not make any HTTP requests.")
    subparsers = parser.add_subparsers(dest='command', help="Mode of operation for integrations.py.")
    
    # Parser for create
    parser_create = subparsers.add_parser('create', help='Create a set of new integrations')
    parser_create.add_argument('-f', '--file', help="Config file containing info about the integrations", required=True)

    # Parser for view
    parser_view = subparsers.add_parser('view', help="See the currently existing integrations")

    # Parser for delete
    parser_delete = subparsers.add_parser('delete', help="Delete integrations")

    return parser


def run_command(parser):
    args = parser.parse_args()
    cmd = args.command

    modes = {
        'create': create.create,
        'view':   view.view,
        'delete': delete.delete
    }

    if cmd not in modes:
        parser.print_help()
        sys.exit(1)

    modes[cmd](args)


def main():
    parser = build_parser()
        
    run_command(parser)

    with open(args.file) as f:
        conf = json.load(f)
        
    api_utils.validate_key(conf['api_key'], conf['kibana_url'])

    i = 1
    for node in conf['nodes']:
        print(f"Creating integrations for node {i} of {len(conf['nodes'])} ({node['hostname']})")
        i += 1

        create_integrations(node, conf['api_key'], conf['kibana_url'])


if __name__ == "__main__":
    main()
