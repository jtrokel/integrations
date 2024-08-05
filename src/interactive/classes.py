import re


class ExitException(Exception):
    pass


class Page:
    def __init__(self, lines, lnums):
        self.nlines = len(lines)
        self.lines = lines
        self.lnums = lnums

    def select(self, which):
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


class PageList:
    def __init__(self, pages):
        self.npages = len(pages)
        self.pages = pages
        self.itemno = []
        self.cpage = 0
        self.selected = set()
        self.clear_lines = 8
        self.cmd = ""

        i = 1
        for page in self.pages:
            self.itemno.append(range(i, i + page.nlines))
            i += page.nlines
