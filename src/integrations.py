#!/usr/bin/env python3

"""Project to work with Elastic Agent integrations
to import PCP metrics from remote hosts using the Kibana API.

This is the file which should be run - it passes control to other files to do the hard work.

Usage details such as command-line arguments are in the README.
"""

import argparse
import sys

import constants
from modes import create, delete, ilist, update


def build_parser():
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser("./integrations.py")
    subparsers = parser.add_subparsers(
        dest="command", help="Mode of operation for integrations.py."
    )

    # Parser for create
    parser_create = subparsers.add_parser(
        "create", help="Create a set of new integrations"
    )
    parser_create.add_argument(
        "file", help="Config file containing info about the integrations"
    )
    parser_create.add_argument(
        "--check-config",
        action="store_true",
        help="Validate the structure of the config file"
        " and do not make any HTTP requests.",
    )
    parser_create.add_argument(
        "-o",
        "--out",
        help="Path to output file containing mapping of"
        " created integrations' names to ids."
        " Defaults to config/id-map.json",
        default=constants.ROOT_DIR + "/config/id-map.json",
    )
    parser_create.add_argument(
        "--no-outfile",
        help="Disable the creation of a JSON file"
        " mapping created integration names to Kibana ids",
        action="store_false",
        dest="outfile",
    )

    # Parser for list
    subparsers.add_parser("list", help="List the currently existing integrations")

    # Parser for delete
    parser_delete = subparsers.add_parser("delete", help="Delete integrations")
    parser_delete.add_argument(
        "file", help="File containing names or ids of integrations to delete"
    )
    parser_delete.add_argument(
        "-m",
        "--mapfile",
        help="File containing JSON map of integration names to ids."
        " Defaults to config/id-map.json",
        default=constants.ROOT_DIR + "/config/id-map.json",
    )
    parser_delete.add_argument(
        "--generate-map",
        help="Instead of reading name->id map from a file,"
        " generate it by parsing the response from an HTTP request",
        action="store_true",
    )
    parser_delete.add_argument(
        "--check-config",
        action="store_true",
        help="Validate the structure of the config file"
        " and do not make any HTTP requests.",
    )
    parser_delete.add_argument(
        "--regex",
        help="Treat integration names in file as regex"
        " when deciding which integrations to delete",
        action="store_true",
    )
    parser_delete.add_argument(
        "-i",
        "--interactive",
        help="Ask for confirmation before each deletion",
        action="store_true",
    )

    # Parser for update
    subparsers.add_parser(
        "update", help="Update various things about existing integrations"
    )

    return parser


def validate_args(args):
    """Perform various validity checks on command-line arguments.

    Currently:
    Create: check that at most one of -o and --no-outfile are specified.
    """
    if args.command == "create":
        if args.out and not args.outfile:
            print(
                "Can only specify at most one of -o(--out) and --no-outfile.",
                file=sys.stderr,
            )
            sys.exit(1)
    # Can add more as needed


def run_command(parser):
    """Run the command provided by the user."""
    args = parser.parse_args()
    validate_args(args)
    cmd = args.command

    modes = {
        constants.CREATE: (create.create, ("args",)),
        constants.LIST: (ilist.ilist, ()),
        constants.DELETE: (delete.delete, ("args",)),
        constants.UPDATE: (update.update, ()),
    }

    for command, (func, param_types) in modes.items():
        if cmd == command:
            params = []
            for ptype in param_types:
                if ptype == "args":
                    params.append(args)
            func(*params)


def main():
    """The driver for integrations.py."""
    parser = build_parser()

    run_command(parser)


if __name__ == "__main__":
    main()
