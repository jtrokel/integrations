#!/usr/bin/env python3

import os
import json
import requests
import argparse
import sys

import constants
from utils import api_utils
from modes import create, view, delete 

def build_parser():
    parser = argparse.ArgumentParser("integrations")
    parser.add_argument('--check-config', action='store_true', help="Validate the structure of the config file passed to -f and do not make any HTTP requests.")
    subparsers = parser.add_subparsers(dest='command', help="Mode of operation for integrations.py.")
    
    # Parser for create
    parser_create = subparsers.add_parser('create', help='Create a set of new integrations')
    parser_create.add_argument('-f', '--file', help="Config file containing info about the integrations", required=True)
    parser_create.add_argument('-o', '--out', help="Path to output file containing mapping of created integrations' names to ids")
    parser_create.add_argument('--no-outfile', help="Disable the creation of a JSON file mapping created integration names to Kibana ids", action='store_false', dest='outfile')

    # Parser for view
    parser_view = subparsers.add_parser('view', help="See the currently existing integrations")

    # Parser for delete
    parser_delete = subparsers.add_parser('delete', help="Delete integrations")

    return parser


def run_command(parser):
    args = parser.parse_args()
    cmd = args.command

    modes = {
        constants.CREATE: create.create,
        constants.VIEW:   view.view,
        constants.DELETE: delete.delete
    }

    if cmd not in modes:
        parser.print_help()
        sys.exit(1)

    modes[cmd](args)


def main():
    parser = build_parser()

    run_command(parser)

    #with open(args.file) as f:
    #    conf = json.load(f)
        
    #api_utils.validate_key(conf['api_key'], conf['kibana_url'])

    #i = 1
    #for node in conf['nodes']:
    #    print(f"Creating integrations for node {i} of {len(conf['nodes'])} ({node['hostname']})")
    #    i += 1

    #    create_integrations(node, conf['api_key'], conf['kibana_url'])


if __name__ == "__main__":
    main()
