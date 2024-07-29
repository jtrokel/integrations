"""Driver for the create command.
"""

import constants
from utils import api_utils, file_utils

def iter_nodes(config, args):
    """On each host and group specified in config:

    Build an HTTP request.
    Send an HTTP request.
    Optionally update name->id mapping.
    """
    if args.outfile:
        id_map = {}

    i = 1
    for node in config['nodes']:
        print(f"Creating integrations for node {i} of {len(config['nodes'])} ({node['fqdn']})")
        i += 1

        fqdn = node['fqdn']
        for group in node['groups']:
            group['fqdn'] = fqdn
            # file_utils.expand_metrics(group)
            req = api_utils.build_request(config, constants.CREATE, group)
            mapping = api_utils.request(req, constants.CREATE)
            if args.outfile:
                id_map.update(mapping)

    if args.outfile:
        file_utils.update_idmap(id_map, args)
        print(f"Wrote name->id map to {args.out}")


def create(args):
    """Load config and perform validations."""
    web_info = file_utils.read_config()
    config = file_utils.load_file(args.file)

    if args.check_config:
        file_utils.check_conf(config, constants.CREATE)
    if args.outfile:
        file_utils.try_init_json(args.out)

    api_utils.validate_key(web_info['kibana']['api_key'], web_info['kibana']['kibana_url'])

    iter_nodes(config, args)
