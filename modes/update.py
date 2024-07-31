import time
import re

from utils import apiutils, fileutils

class Page:
    nlines = 0 
    lines = []    
    lnums = []

    def __init__(self, lines, lnums):
        self.nlines = len(lines)
        self.lines = lines
        self.lnums = lnums

    def display(self):
        for pair in zip(self.lnums, self.lines):
            print(f"{f'{pair[0]}: ':<5}{pair[1]}")

    def select(self, which):
        out = []
        for pair in zip(self.lnums, range(len(self.lines))):
            if pair[0] in which:
                old = self.lines[pair[1]]
                if old.startswith('\033'):
                    continue
                self.lines[pair[1]] = f"\033[32m{old}\033[0m"
                out.append(old)
        return out

    def deselect(self, which):
        out = []
        ansi = re.compile(r"\033\[\d+m")
        for pair in zip(self.lnums, range(len(self.lines))):
            if pair[0] in which:
                old = self.lines[pair[1]]
                if not old.startswith('\033'):
                    continue
                self.lines[pair[1]] = ansi.sub('', old)
                out.append(self.lines[pair[1]])
        return out


class PageList:

    def __init__(self, pages):
        self.npages = len(pages)
        self.pages = pages
        self.itemno = []
        self.cpage = 0
        self.selected = set()
        self.clear_lines = 8

        i = 1
        for page in self.pages:
            self.itemno.append(range(i, i + page.nlines))
            i += page.nlines

    def handle_selection_command(self, cmd):
        valid = re.compile(r'[npfb]|(s|d)(a|\d+|\d+-\d+)|\d+j')
        single = re.compile(r'([sd])(\d+)$')
        batch = re.compile(r'([sd])(\d+)-(\d+)')
        jump = re.compile(r'(\d+)j')
        m = valid.match(cmd)

        if not m:
            print("Unrecognized command.")
            time.sleep(0.5)
            self.clear_lines += 1

        elif cmd == 'b':
            return False

        elif cmd == 'f':
            search = input("\033[1m\033[32mSearch\033[0m>> ")
            self.clear_lines += 1
            new_lines = []
            for page in self.pages:
                for line in page.lines:
                    if re.search(search, line):
                        new_lines.append(line)

            if not new_lines:
                print("Search matched nothing.")
                return True

            new_pages = [Page(new_lines[i:i + 15], list(range(i + 1, i + 16))) for i in range(0, len(new_lines), 15)]
            new_pl = PageList(new_pages)
            new_pl.selected = self.selected
            self.selected = new_pl.selection()
            # Redraw
            for i in range(len(self.pages)):
                for j in range(len(self.pages[i].lines)):
                    tmp = self.pages[i].lines[j]
                    if re.sub(r'\033\[\d+m', '', tmp) in self.selected and not tmp.startswith('\033'):
                        self.pages[i].lines[j] = f"\033[32m{tmp}\033[0m"
                    elif re.sub(r'\033\[\d+m', '', tmp) not in self.selected and tmp.startswith('\033'):
                        self.pages[i].lines[j] = re.sub(r'\033\[\d+m', '', tmp)

        elif cmd == 'n':
            if self.cpage >= self.npages - 1:
                print("At last page already.")
                self.clear_lines += 1
                time.sleep(0.5)
            else:
                self.cpage += 1

        elif cmd == 'p':
            if self.cpage <= 0:
                print("At first page already.")
                self.clear_lines += 1
                time.sleep(0.5)
            else:
                self.cpage -= 1

        elif jump.match(cmd):
            jmp = jump.match(cmd)
            jtarget = int(jmp.group(1))
            if jtarget < 1 or jtarget > self.npages:
                print("Invalid page number.")
            else:
                self.cpage = jtarget - 1

        elif cmd == 'sa':
            for i, j in enumerate(self.itemno):
                on = self.pages[i].select(list(j))
                self.selected.update(on)

        elif cmd == 'da':
            for i, j in enumerate(self.itemno):
                off = self.pages[i].deselect(list(j))
                self.selected.difference_update(off)

        elif single.match(cmd):
            sm = single.match(cmd)
            if not self.itemno[self.cpage][0] <= int(sm.group(2)) <= self.itemno[self.cpage][-1]:
                raise ValueError

            if single.match(cmd).group(1) == 's':
                on = self.pages[self.cpage].select([int(sm.group(2))])
                self.selected.update(on)
            else:
                off = self.pages[self.cpage].deselect([int(sm.group(2))])
                self.selected.difference_update(off)

        elif batch.match(cmd):
            bm = batch.match(cmd)
            if (int(bm.group(2)) < self.itemno[0][0]
                or int(bm.group(3)) > self.itemno[-1][-1]
                or int(bm.group(2)) > int(bm.group(3))):
                raise ValueError

            target = set(range(int(bm.group(2)), int(bm.group(3)) + 1))
            if batch.match(cmd).group(1) == 's':
                for i, j in enumerate(self.itemno):
                    on = self.pages[i].select(list(set(j) & target))
                    self.selected.update(on)
            else:
                for i, j in enumerate(self.itemno):
                    off = self.pages[i].deselect(list(set(j) & target))
                    self.selected.difference_update(off)

        return True


    def selection(self):
        self.cpage = 0
        cmd = ''

        while True:
            self.clear_lines = 8
            self.pages[self.cpage].display()
            print(f"\nPage {self.cpage + 1}/{self.npages}\n")
            print("---COMMANDS---")
            print(f"{'n: next page':<20}{'p: previous page':<28}{'f: search':<35}{'b: back/done':<20}")
            print(f"{'sa: select all':<20}{'s<#>: select <#> above':<28}{'s<#>-<#>: select <#>-<#> above':<35}{'<#>j: jump to page <#>':<20}")
            print(f"{'da: deselect all':<20}{'d<#>: deselect <#> above':<28}{'d<#>-<#>: deselect <#>-<#> above':<35}")
            cmd = input("\033[1m\033[36mSelection\033[0m>> ")
            if not self.handle_selection_command(cmd):
                break

            # print(f"\033[{self.pages[self.cpage].nlines + self.clear_lines}F\033[0J\r", end='', flush=True)

        return self.selected


    def update(self):
        cmd = ''
        
        while True:
            print("\n---COMMANDS---")
            print(f"{'e: enable':<22}{'d: disable':<23}{'v: view info':<22}{'l: list selected':<25}")
            print(f"{'a: add metrics':<22}{'r: remove metrics':<23}{'i: change interval':<22}{'p: change pmproxy url':<25}")
            print(f"{'d: change policy id':<22}{'c: create config file':<23}{'b: back to selection':<22}")
            cmd = input("\033[1m\033[34mSelection\033[0m>> ")

    def display(self):
        self.selection()
        print(f"Selected:")
        lselected = sorted(list(self.selected), key=key_names)
        for i in range(0, len(lselected), 4):
            try:
                print(f"{lselected[i]:<20}", end='')
                print(f"{lselected[i+1]:<20}", end='')
                print(f"{lselected[i+2]:<20}", end='')
                print(f"{lselected[i+3]:<20}")
            except:
                print() # Flush the print buffer
                break

        self.update()
        

def key_names(name):
    ints = list(map(int, re.findall(r'\d+', name)))
    return (len(ints) == 0, ints, name)


def update():
    # Make map
    # Get list of integration names
    # Build pl
    # Display pl
