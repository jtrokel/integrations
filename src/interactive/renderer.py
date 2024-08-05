import re
import sys
import json

from interactive import commands, classes


def selection(page_list):
    cmd = ""

    while True:
        try:
            page_list.clear_lines = 8
            display_page(page_list.pages[page_list.cpage])
            print(f"\nPage {page_list.cpage + 1}/{page_list.npages}\n")
            print("---COMMANDS---")
            print(
                f"{'n: next page':<20}{'p: previous page':<28}{'f: search':<35}{'b: back/done':<20}"
            )
            print(
                f"{'sa: select all':<20}{'s<#>: select <#> above':<28}{'s<#>-<#>: select <#>-<#> above':<35}{'<#>j: jump to page <#>':<20}"
            )
            print(
                f"{'da: deselect all':<20}{'d<#>: deselect <#> above':<28}{'d<#>-<#>: deselect <#>-<#> above':<35}"
            )
            cmd = input("\033[1m\033[36mSelection\033[0m>> ")
            commands.handle_select(page_list, cmd)
        except classes.ExitException:
            break

        # print(f"\033[{self.pages[self.cpage].nlines + self.clear_lines}F\033[0J\r", end='', flush=True)

    return page_list.selected


def update(selected, name_map, config):
    req_bodies = []  # Will have bodies to send in put requests
    for integration in selected:
        body = commands.transform_body(name_map[integration])
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

    cmd = ""
    applied = True

    while True:
        try:
            print("\n---COMMANDS---")
            print(
                f"{'e: enable':<24}{'d: disable':<23}{'v: view selected':<22}{'s: apply changes':<25}"
            )
            print(
                f"{'a: add metrics':<24}{'r: remove metrics':<23}{'i: change interval':<22}{'u: change pmproxy url':<25}"
            )
            print(
                f"{'t: see unsent updates':<24}{'c: create config file':<23}{'q: quit':<22}"
            )
            cmd = input("\033[1m\033[34mSelection\033[0m>> ")
            applied = commands.handle_update(
                selected, name_map, req_bodies, cmd, applied, config
            )
        except classes.ExitException:
            break

    print("<3")


def display_page(page):
    for pair in zip(page.lnums, page.lines):
        print(f"{f'{pair[0]}: ':<5}{pair[1]}")


def display_pl(page_list, name_map, config):
    selected = selection(page_list)
    if not selected:
        print("Nothing selected, exiting...")
        sys.exit(0)

    print("\nSelected:")
    lselected = sorted(list(selected), key=key_names)
    for i in range(0, len(lselected), 4):
        try:
            print(f"{lselected[i]:<20}", end="")
            print(f"{lselected[i+1]:<20}", end="")
            print(f"{lselected[i+2]:<20}", end="")
            print(f"{lselected[i+3]:<20}")
        except:  # Index out of bounds
            print()  # Flush the buffer
            break

    update(lselected, name_map, config)


def key_names(name):
    ints = list(map(int, re.findall(r"\d+", name)))
    return (len(ints) == 0, ints, name)
