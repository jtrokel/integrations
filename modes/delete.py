"""Driver for the delete command.
"""

import constants
from utils import api_utils, file_utils

def delete(args):
    config = file_utils.load_file(args.file)

    if args.check_config:
        file_utils.check_conf(config, constants.DELETE)
    
    api_utils.validate_key(config['api_key'], config['kibana_url'])
