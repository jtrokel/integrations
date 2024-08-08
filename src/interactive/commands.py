"""Logic for the available commands in update mode's interactive CLI.
"""

import re
from typing import Optional
import time
import json

import requests

from utils import api_utils
from interactive import renderer, classes
import constants


class GenericCommandHandler:
    """Superclass for handlers in interactive mode."""

    def __init__(
        self,
        commands: dict,
    ):
        self.commands = commands
        self.cmd: str = ""
        self.exit: bool = False

    def execute(self, cmd: str) -> Optional[bool]:
        """Decide which command to pass execution to,
        and construct parameters."""
        self.cmd: str = cmd
        for pattern, func in self.commands.items():
            match = re.match(pattern, self.cmd)
            if match:
                return func()

        print("Unrecognized command.")
        time.sleep(0.5)
        return None

    def parse_variable_command(self) -> tuple:
        """Parses a command containing line/page numbers.

        These variable commands are all of the form:
        [cmd][target].
        This function relies on that.
        """
        for i, char in enumerate(self.cmd):
            if str.isdigit(char):
                first_digit = i
                break
        else:
            # No digits found in cmd
            raise RuntimeError("No digit found in variable command.")

        return (self.cmd[:first_digit], self.cmd[first_digit:])


class SelectHandler(GenericCommandHandler):
    """Handler and commands for selection."""

    def __init__(self, page_list):
        self.page_list = page_list
        self.cmd = ""
        super().__init__(
            {
                r"b": self.done,
                r"f": self.search,
                r"n": self.next_page,
                r"p": self.prev_page,
                r"j\d+": self.jump_to,
                r"sa": self.select_all,
                r"da": self.deselect_all,
                r"[sd]\d+$": self.single_item,
                r"[sd]\d+-\d+": self.batch_items,
            }
        )

    def selected(self):
        """Return selected integrations."""
        return self.page_list.selected

    def done(self):
        """Finished selecting, or finished searching."""
        self.exit = True

    def search(self):
        """Search for integrations containing a query string,
        and build a new PageList containing them.
        """

        query = input("\033[1m\033[32mSearch\033[0m>> ")
        new_lines = [
            line
            for page in self.page_list.pages
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
        new_pl.selected = self.page_list.selected
        self.page_list.selected = renderer.selection(new_pl)

        self.page_list.update_colors()

    def next_page(self):
        """Page forward once."""
        if self.page_list.cpage >= self.page_list.npages - 1:
            print("At last page already.")
            time.sleep(0.5)
        else:
            self.page_list.cpage += 1

    def prev_page(self):
        """Page backward once."""
        if self.page_list.cpage <= 0:
            print("At first page already.")
            time.sleep(0.5)
        else:
            self.page_list.cpage -= 1

    def jump_to(self):
        """Go to specified page."""
        __, jtarget = self.parse_variable_command()
        jtarget = int(jtarget)
        if jtarget < 1 or jtarget > self.page_list.npages:
            print("Invalid page number.")
            time.sleep(0.5)
        else:
            self.page_list.cpage = jtarget - 1

    def select_all(self):
        """Select every integration."""
        for i, line_nums in enumerate(self.page_list.all_line_nums):
            on = self.page_list.pages[i].select(list(line_nums))
            self.page_list.selected.update(on)

    def deselect_all(self):
        """Deselect every integration."""
        for i, line_nums in enumerate(self.page_list.all_line_nums):
            off = self.page_list.pages[i].deselect(list(line_nums))
            self.page_list.selected.difference_update(off)

    def single_item(self):
        """Select or deselect a single specified integration."""
        mode, target = self.parse_variable_command()
        target = int(target)

        if (
            not self.page_list.all_line_nums[self.page_list.cpage][0]
            <= target
            <= self.page_list.all_line_nums[self.page_list.cpage][-1]
        ):
            print("Item not on page.")
            time.sleep(0.5)
            return

        if mode == "s":
            on = self.page_list.pages[self.page_list.cpage].select([target])
            self.page_list.selected.update(on)
        else:
            off = self.page_list.pages[self.page_list.cpage].deselect([target])
            self.page_list.selected.difference_update(off)

    def batch_items(self):
        """Select or deselect a specified batch of integrations."""
        mode, target_range = self.parse_variable_command()
        # target_range looks like \d+-\d+
        start, end = [int(i) for i in target_range.split("-")]

        if (
            start < self.page_list.all_line_nums[0][0]
            or end > self.page_list.all_line_nums[-1][-1]
        ):
            print("Item index out of bounds.")
            time.sleep(0.5)
            return

        if start > end:
            print("First index must be smaller than second.")
            time.sleep(0.5)
            return

        target = set(range(start, end + 1))
        if mode == "s":
            for i, line_nums in enumerate(self.page_list.all_line_nums):
                on = self.page_list.pages[i].select(list(set(line_nums) & target))
                self.page_list.selected.update(on)
        else:
            for i, line_nums in enumerate(self.page_list.all_line_nums):
                off = self.page_list.pages[i].deselect(list(set(line_nums) & target))
                self.page_list.selected.difference_update(off)


class UpdateHandler(GenericCommandHandler):
    """Handler and commands for update."""

    def __init__(self, selected: list, name_map: dict, config: dict, dupes: bool):
        self.selected = selected
        self.name_map = name_map
        self.config = config
        self.allow_duplicates = dupes
        self.applied = True
        self.edits = {
            name: {
                "enabled": None,  # Will be string
                "hostname": None,  # Will be string
                "interval": None,  # Will be string
                "url": None,  # Will be string
                "added_metrics": None,  # Will be list
                "removed_metrics": None,  # Will be list
            }
            for name in name_map
            if name in selected
        }
        self.req_bodies = self.init_reqs()
        super().__init__(
            {
                "e": self.enable,
                "d": self.disable,
                "v": self.view,
                "q": self.quit_cli,
                "s": self.save,
                "a": self.add_metrics,
                "r": self.remove_metrics,
                "i": self.change_interval,
                "u": self.change_url,
                "t": self.see_updates,
                "c": self.create_config,
                "h": self.update_help,
            },
        )

    def init_reqs(self):
        """Create the lighter weight request bodies to be sent in requests."""
        req_bodies = []
        for integration in self.selected:
            body = transform_body(self.name_map[integration])
            for inp in body["inputs"]:
                for stream in body["inputs"][inp]["streams"]:
                    url = re.compile(
                        r"^http:\/\/(.*?)\/pmapi\/fetch\?hostspec=(.*?)&.*&names=(.*)$"
                    )
                    match = url.match(
                        body["inputs"][inp]["streams"][stream]["vars"]["request_url"]
                    )
                    body["hostname_"] = match.group(2)
                    body["pmproxy_url_"] = match.group(1)
                    body["metrics_"] = match.group(3)

            req_bodies.append(body)

        return req_bodies

    def enable(self):
        """Enable selected integrations."""
        try:
            for body in self.req_bodies:
                for inp in body["inputs"]:
                    # AFAIK they're always both True or False, never one and one
                    if not body["inputs"][inp]["enabled"]:
                        self.edits[body["name"]]["enabled"] = "True"
                        body["inputs"][inp]["enabled"] = True
                    for stream in body["inputs"][inp]["streams"]:
                        body["inputs"][inp]["streams"][stream]["enabled"] = True
            self.applied = False
        except KeyError as e:
            print(e)

    def disable(self):
        """Disable selected integrations."""
        try:
            for body in self.req_bodies:
                for inp in body["inputs"]:
                    if body["inputs"][inp]["enabled"]:
                        self.edits[body["name"]]["enabled"] = "False"
                        body["inputs"][inp]["enabled"] = False
                    for stream in body["inputs"][inp]["streams"]:
                        body["inputs"][inp]["streams"][stream]["enabled"] = False
            self.applied = False
        except KeyError as e:
            print(e)

    def view(self):
        """View info about selected integrations."""
        print("\033[1mNon-Metric Info\033[0m")
        print(
            f"{'Integration':<22} | {'Host':<15}{'Enabled':<10}"
            f"{'Interval':<10}{'pmproxy URL':<40}{'Policy ID'}"
        )
        print("-" * 23 + "|" + "-" * 106)

        metrics = []
        for integration in self.selected:
            body = transform_body(self.name_map[integration], extended=True)
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

                    metrics.append(body["metrics_"])

        print("\n\033[1mMetric Info\033[0m")
        for i, integration in enumerate(self.selected):
            print(f"{f'{integration}:':<22}{metrics[i]}\n")

    def quit_cli(self):
        """Quit the CLI."""
        if not self.applied:
            cont = input(
                "You have updates that have not been applied."
                " Are you sure you want to quit? (y/N): "
            )
            if cont != "y":
                return

        self.exit = True

    def save(self):
        """Send HTTP requests containing all specified updates."""
        # TODO: Could probably be parallelized.
        i = 1
        bad_reqs = []
        for body in self.req_bodies:
            try:
                print(
                    f"Updating integration {i} of {len(self.req_bodies)} ({body['name']})."
                )
                i += 1
                tmp = {
                    "kibana_url": self.config["kibana"]["kibana_url"],
                    "api_key": self.config["kibana"]["api_key"],
                }
                tmp.update(body)
                req = api_utils.build_request(
                    tmp, constants.UPDATE, id_=self.name_map[body["name"]]["id"]
                )
                api_utils.request(req, constants.UPDATE)

                for k in self.edits[body["name"]].items():
                    self.edits[body["name"]][k] = None

            except (KeyError, requests.exceptions.RequestException) as e:
                print(e)
                bad_reqs.append(body["name"])

        if bad_reqs:
            print(
                "Updates for integrations " + str(bad_reqs) + " might have failed."
                "You should ensure they are as you expect."
            )

        self.applied = True

    def add_metrics(self):
        """Request and add a list of metrics to selected integrations."""
        valid = re.compile(r"(?:\w+(?:\.\w+)*,?)+")
        metrics = input("\033[34mMetrics\033[0m>> ")
        if not valid.match(metrics):
            print(
                "Invalid metrics. Metrics should be characters separated by dots,"
                " and you should give a comma-separated list of metrics."
            )
            return

        try:
            for body in self.req_bodies:
                mlist = body["metrics_"].split(",")
                to_add = metrics.split(",")
                if not self.allow_duplicates:
                    to_add = list(set(to_add).difference(mlist))

                if self.edits[body["name"]]["added_metrics"] is None:
                    self.edits[body["name"]]["added_metrics"] = []
                self.edits[body["name"]]["added_metrics"].extend(to_add)

                mlist.extend(to_add)
                body["metrics_"] = ",".join(mlist)
            self.applied = False
        except KeyError as e:
            print(e)

    def remove_metrics(self):
        """Request and remove a list of metrics to selected integrations."""
        valid = re.compile(r"(?:\w+(?:\.\w+)*,?)+")
        metrics = input("\033[34mMetrics\033[0m>> ")
        if not valid.match(metrics):
            print(
                "Invalid metrics. Metrics should be characters separated by dots,"
                " and you should give a comma-separated list of metrics."
            )
            return

        try:
            for body in self.req_bodies:
                mlist = body["metrics_"].split(",")
                to_remove = metrics.split(",")

                actual = list(set(to_remove).intersection(mlist))
                if self.edits[body["name"]]["removed_metrics"] is None:
                    self.edits[body["name"]]["removed_metrics"] = []
                self.edits[body["name"]]["removed_metrics"].extend(actual)

                new_mlist = [metric for metric in mlist if metric not in to_remove]
                body["metrics_"] = ",".join(new_mlist)
            self.applied = False
        except KeyError as e:
            print(e)

    def change_interval(self):
        """Request and change the interval for selected integrations."""
        valid = re.compile(r"^[1-9][0-9]*[smh]$")
        new_interval = input("\033[34mInterval\033[0m>> ")
        if not valid.match(new_interval):
            print(
                f"Interval {new_interval} is invalid."
                " It must be in the format <number><unit>, where unit can be s, m, or h."
            )
            return

        try:
            for body in self.req_bodies:
                for inp in body["inputs"]:
                    for stream in body["inputs"][inp]["streams"]:
                        body["inputs"][inp]["streams"][stream]["vars"][
                            "request_interval"
                        ] = new_interval

                        self.edits[body["name"]]["interval"] = new_interval
            self.applied = False
        except KeyError as e:
            print(e)

    def change_url(self):
        """Request and change the pmproxy URL for selected integrations."""
        new_url = input("\033[34mpmproxy URL\033[0m>> ")

        try:
            for body in self.req_bodies:
                body["pmproxy_url_"] = new_url
                self.edits[body["name"]]["url"] = new_url
            self.applied = False
        except KeyError as e:
            print(e)

    def see_updates(self):
        """See the updates that the user's made but not saved so far."""

        def color_wrap(color_code, string):
            return f"\033[{color_code}m{string}\033[0m"

        print(
            "\nChanged fields are shown in \033[35mmagenta\033[0m,"
            " additions are shown in \033[32mgreen\033[0m,"
            " and removals are shown in \033[31mred\033[0m."
        )

        print()
        print(self.edits)
        print()

        print("\033[1mNon-Metric Info\033[0m")
        print(
            f"{'Integration':<22} | {'Host':<15}{'Enabled':<10}"
            f"{'Interval':<10}{'pmproxy URL':<40}{'Policy ID'}"
        )
        print("-" * 23 + "|" + "-" * 106)
        for integration in self.selected:
            body = transform_body(self.name_map[integration], extended=True)
            for inp in body["inputs"]:
                for stream in body["inputs"][inp]["streams"]:

                    enabled = (
                        "True"
                        if body["inputs"][inp]["enabled"]
                        and body["inputs"][inp]["streams"][stream]["enabled"]
                        else "False"
                    )
                    output = {
                        "enabled": [
                            enabled,
                            10,
                        ],
                        "hostname": [body["hostname_"].split(".")[0], 15],
                        "interval": [
                            body["inputs"][inp]["streams"][stream]["vars"][
                                "request_interval"
                            ],
                            10,
                        ],
                        "url": [body["pmproxy_url_"], 40],
                        "policy_id": body["policy_id"],  # Doesn't get formatted
                    }

                    for field in output:
                        if (
                            field in self.edits[integration]
                            and self.edits[integration][field] is not None
                        ):
                            output[field][0] = color_wrap(
                                "35", self.edits[integration][field]
                            )
                            output[field][1] += 9  # Formatting for ANSI escapes

                    print(
                        f"{integration:<22} | {output['hostname'][0]:<{output['hostname'][1]}}"
                        f"{output['enabled'][0]:<{output['enabled'][1]}}"
                        f"{output['interval'][0]:<{output['interval'][1]}}"
                        f"{output['url'][0]:<{output['url'][1]}}{output['policy_id']}"
                    )

        print("\n\033[1mMetric Info\033[0m")
        for integration in self.selected:
            if (
                self.edits[integration]["added_metrics"] is None
                and self.edits[integration]["removed_metrics"] is None
            ):
                out = "No change in metrics."
                print(f"{f'{integration}:':<22}{out}\n")
            else:
                print(
                    f"{f'{integration}: ':<25}{color_wrap('32', '+')}"
                    f" {color_wrap('32', ','.join(self.edits[integration]['added_metrics']))}"
                )
                print(
                    f"{'':<25}{color_wrap('31', '-')}"
                    f" {color_wrap('31', ','.join(self.edits[integration]['removed_metrics']))}\n"
                )

    def create_config(self):
        """Create a sample config file which could be used to create the selected integrations."""
        nodes = []
        targets = [
            body for (name, body) in self.name_map.items() if name in self.selected
        ]

        while targets:
            # targets may have multiple integrations for the same host.
            # We handle this somewhat inefficiently, by iterating through
            # all the targets for each hostname.
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

    def update_help(self):
        """Print help text for the update commands."""
        print("\ne - queue enabling all selected integrations")
        print("d - queue disabling all selected integrations")
        print("v - view all selected integrations without updates")
        print("s - apply all queued updates")
        print("a - queue adding metrics to all selected integrations")
        print("r - queue removing metrics from all selected integrations")
        print("i - queue changing request interval on all selected integrations")
        print("u - queue changing pmproxy URL on all selected integrations")
        print("t - see all queued updates")
        print(
            "c - generate a config file for create mode"
            " corresponding to the selected integrations\n"
        )


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
