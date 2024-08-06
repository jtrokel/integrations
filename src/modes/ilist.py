"""Driver for the list command.
"""

from utils import api_utils, file_utils


def ilist():
    """List each installed integration and whether it's enabled."""
    web_info = file_utils.read_config()
    kib_info = (web_info["kibana"]["api_key"], web_info["kibana"]["kibana_url"])
    api_utils.validate_key(*kib_info)

    idmap = api_utils.generate_map(*kib_info, extended=True)
    print(f"{'Name':<25}{'ID':<45}{'Status'}")
    for name in sorted(idmap.keys()):
        enabled = (
            "\033[32menabled\033[0m"
            if idmap[name]["enabled_"]
            else "\033[31mdisabled\033[0m"
        )
        print(f"{name:<25}{idmap[name]['id']:<45}{enabled}")
