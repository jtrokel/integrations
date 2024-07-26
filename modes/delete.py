"""Driver for the delete command.
"""

import sys
import re

import constants
from utils import api_utils, file_utils


def handle_names(names, args, kib_info, ids):
    idmap = {}
    if args.generate_map:
        idmap = api_utils.generate_map(*kib_info)
    else:
        idmap = file_utils.load_file(args.mapfile)

    for name in names:
        if args.regex:
            # Compile each provided regex, then try matching against each name in map
            try:
                re_name = re.compile(name)
                for mname, mid in idmap.items():
                    opt_name = re_name.match(mname)
                    if opt_name:
                        ids.append(mid)

            except re.error as err:
                print(err.msg + ' in ' + name, file=sys.stderr)
                sys.exit(1)

        else:
            ids.append(idmap.get(name, ''))
            if name not in idmap:
                print(f"Could not find an integration with the name {name}.", file=sys.stderr)
    
    if ('' in ids) and (not args.generate_map):
        ids = [i for i in ids if i != '']
        print(f"Some named integrations were not found in the mapfile."
              " integrations.py will still delete all the ones it found"
              " succesfully. If you haven't mistyped the missing integrations,"
              " try using --generate-map next run.", file=sys.stderr)

    return list(set(ids)) # Don't want duplicates, and order doesn't matter


def delete(args):
    config = file_utils.load_file(args.file)
    kib_info = (config['api_key'], config['kibana_url'])

    if args.check_config:
        file_utils.check_conf(config, constants.DELETE)
    
    api_utils.validate_key(*kib_info)

    ids = config.get('ids', [])
    if 'names' in config:
        ids = handle_names(config['names'], args, kib_info, ids)

    for i in ids: #TODO: Handle args.interactive
        req = api_utils.build_request(config, constants.DELETE, id_=i)
        api_utils.request(req, constants.DELETE)
