import re

from interactive import commands


def selection(page_list):
    cmd = ''

    while True:
        page_list.clear_lines = 8
        display_page(page_list.pages[page_list.cpage]) 
        print(f"\nPage {page_list.cpage + 1}/{page_list.npages}\n")
        print("---COMMANDS---")
        print(f"{'n: next page':<20}{'p: previous page':<28}{'f: search':<35}{'b: back/done':<20}")
        print(f"{'sa: select all':<20}{'s<#>: select <#> above':<28}{'s<#>-<#>: select <#>-<#> above':<35}{'<#>j: jump to page <#>':<20}")
        print(f"{'da: deselect all':<20}{'d<#>: deselect <#> above':<28}{'d<#>-<#>: deselect <#>-<#> above':<35}")
        cmd = input("\033[1m\033[36mSelection\033[0m>> ")
        if not commands.handle_select(page_list, cmd):
            break

        # print(f"\033[{self.pages[self.cpage].nlines + self.clear_lines}F\033[0J\r", end='', flush=True)

    return page_list.selected


def update(page_list):
    cmd = ''

    while True:
        print("\n---COMMANDS---")
        print(f"{'e: enable':<22}{'d: disable':<23}{'v: view info':<22}{'l: list selected':<25}")
        print(f"{'a: add metrics':<22}{'r: remove metrics':<23}{'i: change interval':<22}{'u: change pmproxy url':<25}")
        print(f"{'p: change policy id':<22}{'c: create config file':<23}{'b: back to selection':<22}")
        cmd = input("\033[1m\033[34mSelection\033[0m>> ")
        commands.handle_update(page_list, cmd)


def display_page(page):
    for pair in zip(page.lnums, page.lines):
        print(f"{f'{pair[0]}: ':<5}{pair[1]}")


def display_pl(page_list):
    selected = selection(page_list)
    print("\nSelected:")
    lselected = sorted(list(selected), key=key_names)
    for i in range(0, len(lselected), 4):
        try:
            print(f"{lselected[i]:<20}", end='')
            print(f"{lselected[i+1]:<20}", end='')
            print(f"{lselected[i+2]:<20}", end='')
            print(f"{lselected[i+3]:<20}")
        except: # Index out of bounds
            print() # Flush the buffer
            break

    update(page_list)


def key_names(name):
    ints = list(map(int, re.findall(r'\d+', name)))
    return (len(ints) == 0, ints, name)
