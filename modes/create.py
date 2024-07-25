import constants
from utils import api_utils, file_utils

def iter_nodes(conf, args):
    if args.outfile: 
        id_map = {}

    i = 1
    for node in conf['nodes']:
        print(f"Creating integrations for node {i} of {len(conf['nodes'])} ({node['hostname']})")
        i += 1

        hostname = node['hostname']
        for group in node['groups']:
            group['hostname'] = hostname
            req = api_utils.build_request(conf, constants.CREATE, group)
            mapping = api_utils.request(req, args, constants.CREATE)
            if args.outfile:
                id_map.update(mapping)

    if args.outfile:
        file_utils.update_idmap(id_map, args)


def create(args):
    config = file_utils.load_file(args.file)
    if args.check_config:
        file_utils.check_conf(config, constants.CREATE)

    if args.outfile:
        file_utils.try_init_json(args.out)

    api_utils.validate_key(config['api_key'], config['kibana_url'])

    iter_nodes(config, args)

