"""Driver for the list command.
"""

from utils import api_utils, file_utils


def ilist(args):
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    ENDC = "\033[0m"

    web_info = file_utils.read_config()
    kib_info = (web_info["kibana"]["api_key"], web_info["kibana"]["kibana_url"])
    api_utils.validate_key(*kib_info)

    idmap = api_utils.generate_map(*kib_info, extended=True)
    print(f"{'Name':<25}{'ID':<45}{'Status'}")
    for name in sorted(idmap.keys()):
        enabled = (
            f"{GREEN}enabled{ENDC}"
            if idmap[name]["enabled_"]
            else f"{RED}disabled{ENDC}"
        )
        line = f"{name:<25}{idmap[name]['id']:<45}{enabled}"
        print(line)
