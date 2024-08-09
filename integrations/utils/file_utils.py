"""Functions for working with local files.
"""

import json
import os
import sys
import configparser

import jsonschema

# from pcp import pmapi
# import cpmapi as c_api

import constants


def read_config():
    """Read web_config.ini file."""
    cfg = configparser.ConfigParser()
    cfg.read(f"{constants.ROOT_DIR}/config/web_config.ini")
    return cfg


def load_file(infile):
    """Load JSON from file."""
    with open(infile, encoding="utf-8") as infd:
        try:
            config = json.load(infd)
            return config
        except json.decoder.JSONDecodeError:
            print(
                f"Failed to parse JSON in {infile}. Ensure that it contains valid JSON.",
                file=sys.stderr,
            )
            sys.exit(1)


def check_conf(config, mode):
    """Validate config against a schema, chosen depending on mode."""
    schemas = {
        constants.CREATE: {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "api_key": {"type": "string"},
                "kibana_url": {"type": "string"},
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fqdn": {"type": "string"},
                            "groups": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "policy_id": {"type": "string"},
                                        "pmproxy_url": {"type": "string"},
                                        "interval": {"type": "string"},
                                        "metrics": {"type": "string"},
                                    },
                                    "required": [
                                        "policy_id",
                                        "pmproxy_url",
                                        "interval",
                                        "metrics",
                                    ],
                                },
                            },
                        },
                        "required": ["fqdn", "groups"],
                    },
                },
            },
            "required": ["api_key", "kibana_url", "nodes"],
        },
        constants.LIST: {},
        constants.DELETE: {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "api_key": {"type": "string"},
                "kibana_url": {"type": "string"},
                "names": {"type": "array", "items": {"type": "string"}},
                "ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["api_key", "kibana_url"],
            "oneOf": [{"required": ["names"]}, {"required": ["ids"]}],
        },
        constants.UPDATE: {},
    }

    try:
        jsonschema.validate(config, schemas[mode])
    except jsonschema.exceptions.ValidationError as exception:
        print("Config file is invalid:", file=sys.stderr)
        print(exception.message, file=sys.stderr)

        # TODO: fix this super duper jank
        if "is valid under each of" in exception.message:
            print(
                "Ensure that you haven't specified conflicting keys!", file=sys.stderr
            )
        sys.exit(1)

    print("Config file is valid.")
    sys.exit(0)


# Attempt at expanding metric names
# The pmapi struggles with finding the correct PMNS
"""
def expand_metrics(group):
    expanded = []
    ctx = pmapi.pmContext(c_api.PM_CONTEXT_HOST, group['fqdn'])

    def add_metric(name):
        expanded.append(name)

    for metric in group['metrics'].split(','):
        ctx.pmTraversePMNS(metric, add_metric)

    group['metrics'] = ','.join(expanded)
"""


def try_init_json(path):
    """Create a JSON file if it doesn't exist."""
    if not os.path.isfile(path):
        print(f"Could not find file {path}.")
        cont = input("Do you want to continue and create it automatically? (y/n): ")
        if cont != "y":
            print("Exiting...")
            sys.exit(0)
        with open(path, mode="w", encoding="utf-8") as newfile:
            json.dump({}, newfile)


def update_idmap(new_map, args):
    """Update the name->id mapping with the newly created integrations."""
    with open(args.out, mode="r+", encoding="utf-8") as outfile:
        try:
            file_map = json.load(outfile) if os.path.getsize(args.out) > 0 else {}
            file_map.update(new_map)
            outfile.seek(0)
            json.dump(file_map, outfile)
            # Cleans up if the original map was longer than the new one:
            # Shouldn't happen, but just in case.
            outfile.truncate()
        except json.decoder.JSONDecodeError:
            print(f"Failed to parse JSON in {args.out}.", file=sys.stderr)
            sys.exit(1)
