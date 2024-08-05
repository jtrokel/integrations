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
                for mname, mmap in idmap.items():
                    opt_name = re_name.match(mname)
                    if opt_name:
                        ids.append(mmap["id"])

            except re.error as err:
                print(err.msg + " in " + name, file=sys.stderr)
                sys.exit(1)

        else:
            if name in idmap:
                ids.append(idmap[name]["id"])
            else:
                ids.append("")
                print(
                    f"Could not find an integration with the name {name}.",
                    file=sys.stderr,
                )

    if ("" in ids) and (not args.generate_map):
        ids = [i for i in ids if i != ""]
        print(
            "Some named integrations were not found in the mapfile."
            " integrations.py will still delete all the ones it found"
            " succesfully. If you haven't mistyped the missing integrations,"
            " try using --generate-map next run.",
            file=sys.stderr,
        )

    return (list(set(ids)), idmap)  # Don't want duplicates, and order doesn't matter


def delete(args):
    web_info = file_utils.read_config()
    config = file_utils.load_file(args.file)
    kib_info = (web_info["kibana"]["api_key"], web_info["kibana"]["kibana_url"])
    config["api_key"] = kib_info[0]
    config["kibana_url"] = kib_info[1]

    if args.check_config:
        file_utils.check_conf(config, constants.DELETE)

    api_utils.validate_key(*kib_info)

    ids = config.get("ids", [])
    if "names" in config:
        names_info = handle_names(config["names"], args, kib_info, ids)
        ids = names_info[0]

    for i in ids:
        req = api_utils.build_request(config, constants.DELETE, id_=i)
        if args.interactive:
            if "names" in config:
                inv_map = {val["id"]: key for key, val in names_info[1].items()}
                curr_name = inv_map[i]
                del_this = input(
                    f"Do you want to delete integration {i} ({curr_name})? (y/N) "
                )
            else:
                del_this = input(f"Do you want to delete integration {i}? (y/N) ")

            if del_this != "y":
                continue

        api_utils.request(req, constants.DELETE)
