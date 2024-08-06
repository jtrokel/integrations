"""Logic for the available commands in update mode's interactive CLI.
"""

import re
import time
import json

import requests

from utils import api_utils
from interactive import renderer, classes
import constants


def done():
    """Finished selecting, or finished searching."""
    raise classes.ExitException


def search(page_list):
    """Search for integrations containing a query string,
    and build a new PageList containing them.
    """

    query = input("\033[1m\033[32mSearch\033[0m>> ")
    page_list.clear_lines += 1
    new_lines = [
        line
        for page in page_list.pages
        for line in page.lines
        if re.search(query, line)
    ]

    if not new_lines:
        print("Search matched nothing.")
        time.sleep(0.5)
        return

    new_pages = []
    for i in range(0, len(new_lines), 15):
        line_nums = list(range(i + 1, i + 16))
        lines = new_lines[i : i + 15]
        new_pages.append(classes.Page(lines, line_nums))

    new_pl = classes.PageList(new_pages)
    new_pl.selected = page_list.selected
    page_list.selected = renderer.selection(new_pl)

    page_list.update_colors()


def next_page(page_list):
    """Page forward once."""
    if page_list.cpage >= page_list.npages - 1:
        print("At last page already.")
        page_list.clear_lines += 1
        time.sleep(0.5)
    else:
        page_list.cpage += 1


def prev_page(page_list):
    """Page backward once."""
    if page_list.cpage <= 0:
        print("At first page already.")
        page_list.clear_lines += 1
        time.sleep(0.5)
    else:
        page_list.cpage -= 1


def jump_to(page_list, cmd):
    """Go to specified page."""
    __, jtarget = parse_variable_command(cmd)
    jtarget = int(jtarget)
    if jtarget < 1 or jtarget > page_list.npages:
        print("Invalid page number.")
        time.sleep(0.5)
    else:
        page_list.cpage = jtarget - 1


def select_all(page_list):
    """Select every integration."""
    for i, line_nums in enumerate(page_list.all_line_nums):
        on = page_list.pages[i].select(list(line_nums))
        page_list.selected.update(on)


def deselect_all(page_list):
    """Deselect every integration."""
    for i, line_nums in enumerate(page_list.all_line_nums):
        off = page_list.pages[i].deselect(list(line_nums))
        page_list.selected.difference_update(off)


def single_item(page_list, cmd):
    """Select or deselect a single specified integration."""
    mode, target = parse_variable_command(cmd)
    target = int(target)

    if (
        not page_list.all_line_nums[page_list.cpage][0]
        <= target
        <= page_list.all_line_nums[page_list.cpage][-1]
    ):
        print("Item not on page.")
        time.sleep(0.5)
        return

    if mode == "s":
        on = page_list.pages[page_list.cpage].select([target])
        page_list.selected.update(on)
    else:
        off = page_list.pages[page_list.cpage].deselect([target])
        page_list.selected.difference_update(off)


def batch_items(page_list, cmd):
    """Select or deselect a specified batch of integrations."""
    mode, target_range = parse_variable_command(cmd)
    # target_range looks like \d+-\d+
    start, end = target_range.split("-")

    if start < page_list.all_line_nums[0][0] or end > page_list.all_line_nums[-1][-1]:
        print("Item index out of bounds.")
        time.sleep(0.5)
        return

    if start > end:
        print("First index must be smaller than second.")
        time.sleep(0.5)
        return

    target = set(range(start, end + 1))
    if mode == "s":
        for i, line_nums in enumerate(page_list.all_line_nums):
            on = page_list.pages[i].select(list(set(line_nums) & target))
            page_list.selected.update(on)
    else:
        for i, line_nums in enumerate(page_list.all_line_nums):
            off = page_list.pages[i].deselect(list(set(line_nums) & target))
            page_list.selected.difference_update(off)


def parse_variable_command(cmd):
    """Parses a command containing line/page numbers.

    These variable commands are all of the form:
    [cmd][target].
    This function relies on that.
    """
    for i, char in enumerate(cmd):
        if str.isdigit(char):
            first_digit = i
            break
    else:
        # No digits found in cmd
        raise RuntimeError("No digit found in variable command.")

    return (cmd[:first_digit], cmd[first_digit:])


def handle_select(page_list, cmd):
    """Figure out which select command to execute."""

    commands = {
        r"b": (done, ()),
        r"f": (search, ("page_list",)),
        r"n": (next_page, ("page_list",)),
        r"p": (prev_page, ("page_list",)),
        r"j\d+": (jump_to, ("page_list", "cmd")),
        r"sa": (select_all, ("page_list",)),
        r"da": (deselect_all, ("page_list",)),
        r"[sd]\d+$": (single_item, ("page_list", "cmd")),
        r"[sd]\d+-\d+": (batch_items, ("page_list", "cmd")),
    }

    for pattern, (func, param_types) in commands.items():
        match = re.match(pattern, cmd)
        if match:
            params = []
            for ptype in param_types:
                if ptype == "page_list":
                    params.append(page_list)
                elif ptype == "cmd":
                    params.append(cmd)
            func(*params)
            return

    print("Unrecognized command.")
    time.sleep(0.5)
    page_list.clear_lines += 1
    return


def enable(req_bodies, applied):
    """Enable selected integrations."""
    try:
        for body in req_bodies:
            for inp in body["inputs"]:
                body["inputs"][inp]["enabled"] = True
                for stream in body["inputs"][inp]["streams"]:
                    body["inputs"][inp]["streams"][stream]["enabled"] = True
        return False
    except KeyError as e:
        print(e)
        return applied


def disable(req_bodies, applied):
    """Disable selected integrations."""
    try:
        for body in req_bodies:
            for inp in body["inputs"]:
                body["inputs"][inp]["enabled"] = False
                for stream in body["inputs"][inp]["streams"]:
                    body["inputs"][inp]["streams"][stream]["enabled"] = False
        return False
    except KeyError as e:
        print(e)
        return applied


def view(selected, name_map, applied):
    """View info about selected integrations."""
    print("\033[1mNon-Metric Info\033[0m")
    print(
        f"{'Integration':<22} | {'Host':<15}{'Enabled':<10}"
        f"{'Interval':<10}{'pmproxy URL':<40}{'Policy ID'}"
    )
    print("-" * 23 + "|" + "-" * 106)
    for integration in selected:
        body = transform_body(name_map[integration], extended=True)
        for inp in body["inputs"]:
            for stream in body["inputs"][inp]["streams"]:
                host = body["hostname_"].split(".")[0]
                enabled = (
                    body["inputs"][inp]["enabled"]
                    and body["inputs"][inp]["streams"][stream]["enabled"]
                )
                interval = body["inputs"][inp]["streams"][stream]["vars"][
                    "request_interval"
                ]
                pmproxy_url = body["pmproxy_url_"]
                policy_id = body["policy_id"]
                # Can't get enabled to print 'true' and 'false'
                enabled = "True" if enabled else "False"
                print(
                    f"{integration:<22} | {host:<15}{enabled:<10}"
                    f"{interval:<10}{pmproxy_url:<40}{policy_id}"
                )

    print("\n\033[1mMetric Info\033[0m")
    for integration in selected:
        body = transform_body(name_map[integration], extended=True)
        for inp in body["inputs"]:
            for stream in body["inputs"][inp]["streams"]:
                metrics = body["metrics_"]
                print(f"{f'{integration}:':<22}{metrics}\n")

    return applied


def quit_cli(applied):
    """Quit the CLI."""
    if not applied:
        cont = input(
            "You have updates that have not been applied. Are you sure you want to quit? (y/N): "
        )
        if cont != "y":
            return applied

    raise classes.ExitException


def save(name_map, req_bodies, applied, config):
    """Send HTTP requests containing all specified updates."""
    # TODO: Could probably be parallelized.
    i = 1
    bad_reqs = []
    for body in req_bodies:
        try:
            print(f"Updating integration {i} of {len(req_bodies)} ({body['name']}).")
            i += 1
            tmp = {
                "kibana_url": config["kibana"]["kibana_url"],
                "api_key": config["kibana"]["api_key"],
            }
            tmp.update(body)
            req = api_utils.build_request(
                tmp, constants.UPDATE, id_=name_map[body["name"]]["id"]
            )
            api_utils.request(req, constants.UPDATE)

        except (KeyError, requests.exceptions.RequestException) as e:
            print(e)
            bad_reqs.append(i)

    if bad_reqs:
        print()
        return applied

    return True


def add_metrics(req_bodies, applied):
    """Request and add a list of metrics to selected integrations."""
    valid = re.compile(r"(?:\w+(?:\.\w+)*,?)+")
    metrics = input("\033[34mMetrics\033[0m>> ")
    if not valid.match(metrics):
        print(
            "Invalid metrics. Metrics should be characters separated by dots,"
            " and you should give a comma-separated list of metrics."
        )
        return applied

    try:
        for body in req_bodies:
            mlist = body["metrics_"].split(",")
            to_add = metrics.split(",")
            mlist.extend(to_add)
            body["metrics_"] = ",".join(mlist)
        return False
    except KeyError as e:
        print(e)
        return applied


def remove_metrics(req_bodies, applied):
    """Request and remove a list of metrics to selected integrations."""
    valid = re.compile(r"(?:\w+(?:\.\w+)*,?)+")
    metrics = input("\033[34mMetrics\033[0m>> ")
    if not valid.match(metrics):
        print(
            "Invalid metrics. Metrics should be characters separated by dots,"
            " and you should give a comma-separated list of metrics."
        )
        return applied

    try:
        for body in req_bodies:
            mlist = body["metrics_"].split(",")
            to_remove = metrics.split(",")
            new_mlist = [metric for metric in mlist if metric not in to_remove]
            body["metrics_"] = ",".join(new_mlist)
        return False
    except KeyError as e:
        print(e)
        return applied


def change_interval(req_bodies, applied):
    """Request and change the interval for selected integrations."""
    valid = re.compile(r"^[1-9][0-9]*[smh]$")
    new_interval = input("\033[34mInterval\033[0m>> ")
    if not valid.match(new_interval):
        print(
            f"Interval {new_interval} is invalid."
            " It must be in the format <number><unit>, where unit can be s, m, or h."
        )
        return applied

    try:
        for body in req_bodies:
            for inp in body["inputs"]:
                for stream in body["inputs"][inp]["streams"]:
                    body["inputs"][inp]["streams"][stream]["vars"][
                        "request_interval"
                    ] = new_interval
        return False
    except KeyError as e:
        print(e)
        return applied


def change_url(req_bodies, applied):
    """Request and change the pmproxy URL for selected integrations."""
    new_url = input("\033[34mpmproxy URL\033[0m>> ")

    try:
        for body in req_bodies:
            body["pmproxy_url_"] = new_url
        return False
    except KeyError as e:
        print(e)
        return applied


def see_updates(selected, name_map, req_bodies, applied):
    """See the updates that the user's made but not saved so far."""

    def color_wrap(color_code, string):
        return f"\033[{color_code}m{string}\033[0m"

    print(
        "\nChanged fields are shown in \033[35mmagenta\033[0m,"
        " additions are shown in \033[32mgreen\033[0m,"
        " and removals are shown in \033[31mred\033[0m."
    )
    print("\033[1mNon-Metric Info\033[0m")
    print(
        f"{'Integration':<22} | {'Host':<15}{'Enabled':<10}"
        f"{'Interval':<10}{'pmproxy URL':<40}{'Policy ID'}"
    )
    print("-" * 23 + "|" + "-" * 106)
    for integration in selected:
        old_body = transform_body(name_map[integration], extended=True)
        new_body = [d for d in req_bodies if d["name"] == old_body["name"]][0]
        for inp in old_body["inputs"]:
            for stream in old_body["inputs"][inp]["streams"]:

                eshift = 10
                ishift = 10
                ushift = 40

                host = old_body["hostname_"].split(".")[0]
                new_host = new_body["hostname_"].split(".")[0]
                if host != new_host:
                    new_host = color_wrap("35", new_host)

                enabled = (
                    old_body["inputs"][inp]["enabled"]
                    and old_body["inputs"][inp]["streams"][stream]["enabled"]
                )
                new_enabled = (
                    new_body["inputs"][inp]["enabled"]
                    and new_body["inputs"][inp]["streams"][stream]["enabled"]
                )
                # Can't get enabled to print 'true' and 'false'
                enabled = "True" if enabled else "False"
                new_enabled = "True" if new_enabled else "False"
                if enabled != new_enabled:
                    new_enabled = color_wrap("35", new_enabled)
                    eshift += 9

                interval = old_body["inputs"][inp]["streams"][stream]["vars"][
                    "request_interval"
                ]
                new_interval = new_body["inputs"][inp]["streams"][stream]["vars"][
                    "request_interval"
                ]
                if interval != new_interval:
                    new_interval = color_wrap("35", new_interval)
                    ishift += 9

                pmproxy_url = old_body["pmproxy_url_"]
                new_pmproxy_url = new_body["pmproxy_url_"]
                if pmproxy_url != new_pmproxy_url:
                    new_pmproxy_url = color_wrap("35", new_pmproxy_url)
                    ushift += 9

                policy_id = old_body["policy_id"]
                new_policy_id = new_body["policy_id"]
                if policy_id != new_policy_id:
                    new_policy_id = color_wrap("35", new_policy_id)

                print(
                    f"{integration:<22} | {new_host:<15}{new_enabled:<{eshift}}"
                    f"{new_interval:<{ishift}}{new_pmproxy_url:<{ushift}}{new_policy_id}"
                )

    print("\n\033[1mMetric Info\033[0m")
    for integration in selected:
        old_body = transform_body(name_map[integration], extended=True)
        new_body = [d for d in req_bodies if d["name"] == old_body["name"]][0]
        for inp in old_body["inputs"]:
            for stream in old_body["inputs"][inp]["streams"]:
                old_metrics = old_body["metrics_"]
                new_metrics = new_body["metrics_"]

                out = ""
                if old_metrics == new_metrics:
                    out = "No change in metrics."
                    print(f"{f'{integration}:':<22}{out}\n")
                else:
                    old_list = old_metrics.split(",")
                    new_list = new_metrics.split(",")
                    s_added = set(new_list) - set(old_list)
                    s_removed = set(old_list) - set(new_list)
                    # To keep nice ordering:
                    added = [metric for metric in new_list if metric in s_added]
                    removed = [metric for metric in old_list if metric in s_removed]
                    o_added = color_wrap("32", ",".join(added))
                    o_removed = color_wrap("31", ",".join(removed))
                    print(f"{f'{integration}: ':<25}{color_wrap('32', '+')} {o_added}")
                    print(f"{'':<25}{color_wrap('31', '-')} {o_removed}\n")

    return applied


def create_config(selected, name_map, applied):
    """Create a sample config file which could be used to create the selected integrations."""
    nodes = []
    targets = [body for (name, body) in name_map.items() if name in selected]

    while targets:
        current = targets.pop(0)
        groups = [
            {
                "policy_id": current["policy_id"],
                "pmproxy_url": current["pmproxy_url_"],
                "interval": current["inputs"][0]["streams"][0]["vars"][
                    "request_interval"
                ]["value"],
                "metrics": current["metrics_"],
            }
        ]

        for index, body in enumerate(targets):
            if body["hostname_"] == current["hostname_"]:
                groups.append(
                    {
                        "policy_id": body["policy_id"],
                        "pmproxy_url": body["pmproxy_url_"],
                        "interval": body["inputs"][0]["streams"][0]["vars"][
                            "request_interval"
                        ]["value"],
                        "metrics": body["metrics_"],
                    }
                )
                targets.pop(index)

        nodes.append({"fqdn": current["hostname_"], "groups": groups})

    with open(
        constants.ROOT_DIR + "/config/sample_config.json", "w", encoding="utf-8"
    ) as sample:
        json.dump({"nodes": nodes}, sample)
        print("Wrote config to config/sample_config.json")

    return applied


def transform_body(old_body, extended=False):
    """Change the body of the GET response
    to something that can be sent in the update PUT request.
    """
    if extended:
        good_keys = [
            "package",
            "name",
            "namespace",
            "description",
            "policy_id",
            "vars",
            "hostname_",
            "pmproxy_url_",
            "metrics_",
        ]
    else:
        good_keys = ["package", "name", "namespace", "description", "policy_id", "vars"]
    new_body = {key: old_body[key] for key in good_keys}

    new_body["package"].pop("title", "")

    # Transform inputs
    inputs = old_body["inputs"]
    transformed_inputs = {}

    for input_item in inputs:
        input_type = input_item["type"]
        policy_template = input_item["policy_template"]
        streams = input_item["streams"]

        transformed_inputs[f"{policy_template}-{input_type}"] = {
            "enabled": input_item["enabled"],
            "streams": {},
        }

        for stream in streams:
            stream_data_stream = stream["data_stream"]
            stream_vars = stream["vars"]
            stream_vars_transformed = {
                k: v["value"] for k, v in stream_vars.items() if "value" in v
            }

            transformed_inputs[f"{policy_template}-{input_type}"]["streams"][
                stream_data_stream["dataset"]
            ] = {"enabled": stream["enabled"], "vars": stream_vars_transformed}

    new_body["inputs"] = transformed_inputs
    return new_body


def handle_update(selected, name_map, req_bodies, cmd, applied, config):
    """Figure out which update command to execute."""
    commands = {
        "e": (enable, ("req_bodies", "applied")),
        "d": (disable, ("req_bodies", "applied")),
        "v": (view, ("selected", "name_map", "applied")),
        "q": (quit_cli, ("applied",)),
        "s": (save, ("name_map", "req_bodies", "applied", "config")),
        "a": (add_metrics, ("req_bodies", "applied")),
        "r": (remove_metrics, ("req_bodies", "applied")),
        "i": (change_interval, ("req_bodies", "applied")),
        "u": (change_url, ("req_bodies", "applied")),
        "t": (see_updates, ("selected", "name_map", "req_bodies", "applied")),
        "c": (create_config, ("selected", "name_map", "applied")),
    }

    for command, (func, param_types) in commands.items():
        if cmd == command:
            params = []
            for ptype in param_types:
                if ptype == "selected":
                    params.append(selected)
                elif ptype == "name_map":
                    params.append(name_map)
                elif ptype == "req_bodies":
                    params.append(req_bodies)
                elif ptype == "applied":
                    params.append(applied)
                elif ptype == "config":
                    params.append(config)
            return func(*params)

    print("Unrecognized command.")
    time.sleep(0.5)
    return applied
