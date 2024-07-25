#!/usr/bin/env python3

"""Project to work with Elastic Agent integrations
to import PCP metrics from remote hosts using the Kibana API.

This is the file which should be run - it passes control to other files to do the hard work.

Usage details such as command-line arguments are in the README.
"""

import argparse
import sys

import constants
from modes import create, view, delete

def build_parser():
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(prog="integrations",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--check-config', action='store_true',
                        help="Validate the structure of the config file"
                        " passed to -f and do not make any HTTP requests.")
    subparsers = parser.add_subparsers(dest='command',
                                       help="Mode of operation for integrations.py.")

    # Parser for create
    parser_create = subparsers.add_parser('create', help='Create a set of new integrations')
    parser_create.add_argument('-f', '--file',
                               help="Config file containing info about the integrations",
                               required=True)
    parser_create.add_argument('-o', '--out',
                               help="Path to output file containing mapping of"
                               " created integrations' names to ids."
                               " Defaults to config/id-map.json",
                               default=constants.ROOT_DIR + "/config/id-map.json")
    parser_create.add_argument('--no-outfile',
                               help="Disable the creation of a JSON file"
                               " mapping created integration names to Kibana ids",
                               action='store_false', dest='outfile')

    # Parser for view
    parser_view = subparsers.add_parser('view', help="See the currently existing integrations")

    # Parser for delete
    parser_delete = subparsers.add_parser('delete', help="Delete integrations")

    return parser


def validate_args(args):
    """Perform various validity checks on command-line arguments.

    Currently:
    Check that at most one of -o and --no-outfile are specified.
    """
    if args.out and not args.outfile:
        print("Can only specify at most one of -o(--out) and --no-outfile.")
        sys.exit(1)
    # Can add more as needed


def run_command(parser):
    """Run the command provided by the user."""
    args = parser.parse_args()

    validate_args(args)

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
    """The driver for integrations.py."""
    parser = build_parser()

    run_command(parser)


if __name__ == "__main__":
    main()
