"""Driver for the update command.
"""

from interactive import renderer, classes
from utils import api_utils, file_utils


def update():
    """Build pages for selecting integrations, then pass control."""
    # Make map
    web_info = file_utils.read_config()
    name_map = api_utils.generate_map(
        web_info["kibana"]["api_key"], web_info["kibana"]["kibana_url"], extended=True
    )
    # Get list of integration names
    names = sorted(name_map.keys(), key=renderer.key_names)
    # Build pl
    pages = []
    for i in range(0, len(names), 15):
        line_nums = list(range(i + 1, i + 16))
        lines = names[i : i + 15]
        pages.append(classes.Page(lines, line_nums))
    pl = classes.PageList(pages)
    # Display pl
    renderer.display_pl(pl, name_map, web_info)
