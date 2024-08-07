"""Class definitions for the interactive CLI.
"""

import re


class ExitException(Exception):
    """Used to check if exit command was executed."""


class Page:
    """Each individual page containing integrations."""

    def __init__(self, lines, lnums=None):
        self.nlines = len(lines)
        self.lines = lines
        self.lnums = lnums

    def select(self, which):
        """Change integration to green if it isn't already."""
        out = []
        for pair in zip(self.lnums, range(len(self.lines))):
            if pair[0] in which:
                old = self.lines[pair[1]]
                if old.startswith("\033"):
                    continue
                self.lines[pair[1]] = f"\033[32m{old}\033[0m"
                out.append(old)
        return out

    def deselect(self, which):
        """Change integration to white if it isn't already."""
        out = []
        ansi = re.compile(r"\033\[\d+m")
        for pair in zip(self.lnums, range(len(self.lines))):
            if pair[0] in which:
                old = self.lines[pair[1]]
                if not old.startswith("\033"):
                    continue
                self.lines[pair[1]] = ansi.sub("", old)
                out.append(self.lines[pair[1]])
        return out

    def display(self):
        """Display a page and it's associated line numbers."""
        for pair in zip(self.lnums, self.lines):
            print(f"{f'{pair[0]}: ':<5}{pair[1]}")


class PageList:
    """The list of all the pages."""

    def __init__(self, pages):
        self.npages = len(pages)
        self.pages = pages
        self.all_line_nums = []
        self.cpage = 0
        self.selected = set()
        self.clear_lines = 8
        self.cmd = ""

        i = 1
        for page in self.pages:
            self.all_line_nums.append(range(i, i + page.nlines))
            i += page.nlines

    def display_page(self):
        """Display the current page."""
        self.pages[self.cpage].display()
        print(f"\nPage {self.cpage + 1}/{self.npages}\n")

    def update_colors(self):
        """Redraw the colors for selected integrations."""
        for i, page in enumerate(self.pages):
            for j, line in enumerate(page.lines):
                if re.sub(
                    r"\033\[\d+m", "", line
                ) in self.selected and not line.startswith("\033"):
                    self.pages[i].lines[j] = f"\033[32m{line}\033[0m"
                elif re.sub(
                    r"\033\[\d+m", "", line
                ) not in self.selected and line.startswith("\033"):
                    self.pages[i].lines[j] = re.sub(r"\033\[\d+m", "", line)
