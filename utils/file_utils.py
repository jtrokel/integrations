"""Functions for working with local files.
"""

import json
import os
import sys

import jsonschema

import constants

def load_file(infile):
    """Load JSON from file."""
    with open(infile) as infd:
        try:
            config = json.load(infd)
            return config
        except json.decoder.JSONDecodeError:
            print(f"Failed to parse JSON in {infile}. Ensure that it contains valid JSON.")
            sys.exit(1)


def check_conf(config, mode):
    """Validate config against a schema, chosen depending on mode."""
    schemas = {
        constants.CREATE: {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string"
                },
                "kibana_url": {
                    "type": "string"
                },
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hostname": {
                                "type": "string"
                            },
                            "groups": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "policy_id": {
                                            "type": "string"
                                        },
                                        "pmproxy_url": {
                                            "type": "string"
                                        },
                                        "interval": {
                                            "type": "string"
                                        },
                                        "metrics": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "policy_id",
                                        "pmproxy_url",
                                        "interval",
                                        "metrics"
                                    ]
                                }
                            }
                        },
                        "required": [
                            "hostname",
                            "groups"
                        ]
                    }
                }
            },
            "required": [
                "api_key",
                "kibana_url",
                "nodes"
            ]
        },
        constants.VIEW:   {},
        constants.DELETE: {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string"
                },
                "kibana_url": {
                    "type": "string"
                },
                "names": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "ids": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "api_key",
                "kibana_url"
            ],
            "oneOf": [
                {"required": ["names"]},
                {"required": ["ids"]}
            ]
        }
    }

    try:
        jsonschema.validate(config, schemas[mode])
    except jsonschema.exceptions.ValidationError as exception:
        print("Config file is invalid:")
        print(exception.message)
        if "is valid under each of" in exception.message:
            print("Ensure that you haven't specified conflicting keys!") 
        sys.exit(1)

    print("Config file is valid.")
    sys.exit(0)


def try_init_json(path):
    """Create a JSON file if it doesn't exist."""
    try:
        tmp = open(path)
        tmp.close()
    except FileNotFoundError:
        print(f"Could not find file {path}.")
        cont = input("Do you want to continue and create it automatically? (y/n): ")
        if cont != 'y':
            print("Exiting...")
            sys.exit(0)
    except OSError:
        print(f"Error opening {path}. Try checking its permissions.")
        sys.exit(1)

    if not os.path.isfile(path):
        with open(path, mode='w') as newfile:
            json.dump({}, newfile)


def update_idmap(new_map, args):
    """Update the name->id mapping with the newly created integrations."""
    with open(args.out, mode='r+') as outfile:
        try:
            if os.path.getsize(args.out) > 0:
                file_map = json.load(outfile)
            else:
                file_map = {}
            file_map.update(new_map)
            outfile.seek(0)
            json.dump(file_map, outfile)
            # Cleans up if the original map was longer than the new one:
            # Shouldn't happen, but just in case.
            outfile.truncate()
        except json.decoder.JSONDecodeError:
            print(f"Failed to parse JSON in {args.out}.")
            sys.exit(1)
