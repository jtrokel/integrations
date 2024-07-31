import re
import time

from interactive import renderer, classes


def handle_select(page_list, cmd):
    valid = re.compile(r'[npfb]|(s|d)(a|\d+|\d+-\d+)|\d+j')
    single = re.compile(r'([sd])(\d+)$')
    batch = re.compile(r'([sd])(\d+)-(\d+)')
    jump = re.compile(r'(\d+)j')
    m = valid.match(cmd)

    if not m:
        print("Unrecognized command.")
        time.sleep(0.5)
        page_list.clear_lines += 1

    elif cmd == 'b':
        return False

    elif cmd == 'f':
        search = input("\033[1m\033[32mSearch\033[0m>> ")
        page_list.clear_lines += 1
        new_lines = []
        for page in page_list.pages:
            for line in page.lines:
                if re.search(search, line):
                    new_lines.append(line)

        if not new_lines:
            print("Search matched nothing.")
            return True

        new_pages = []
        for i in range(0, len(new_lines), 15):
            line_nums = list(range(i + 1, i + 16))
            lines = new_lines[i:i + 15]
            new_pages.append(classes.Page(lines, line_nums))
        new_pl = classes.PageList(new_pages)
        new_pl.selected = page_list.selected
        page_list.selected = renderer.selection(new_pl)
        # Redraw
        for i in range(len(page_list.pages)):
            for j in range(len(page_list.pages[i].lines)):
                tmp = page_list.pages[i].lines[j]
                if re.sub(r'\033\[\d+m', '', tmp) in page_list.selected and not tmp.startswith('\033'):
                    page_list.pages[i].lines[j] = f"\033[32m{tmp}\033[0m"
                elif re.sub(r'\033\[\d+m', '', tmp) not in page_list.selected and tmp.startswith('\033'):
                    page_list.pages[i].lines[j] = re.sub(r'\033\[\d+m', '', tmp)

    elif cmd == 'n':
        if page_list.cpage >= page_list.npages - 1:
            print("At last page already.")
            page_list.clear_lines += 1
            time.sleep(0.5)
        else:
            page_list.cpage += 1

    elif cmd == 'p':
        if page_list.cpage <= 0:
            print("At first page already.")
            page_list.clear_lines += 1
            time.sleep(0.5)
        else:
            page_list.cpage -= 1

    elif jump.match(cmd):
        jmp = jump.match(cmd)
        jtarget = int(jmp.group(1))
        if jtarget < 1 or jtarget > page_list.npages:
            print("Invalid page number.")
        else:
            page_list.cpage = jtarget - 1

    elif cmd == 'sa':
        for i, j in enumerate(page_list.itemno):
            on = page_list.pages[i].select(list(j))
            page_list.selected.update(on)

    elif cmd == 'da':
        for i, j in enumerate(page_list.itemno):
            off = page_list.pages[i].deselect(list(j))
            page_list.selected.difference_update(off)

    elif single.match(cmd):
        sm = single.match(cmd)
        if not page_list.itemno[page_list.cpage][0] <= int(sm.group(2)) <= page_list.itemno[page_list.cpage][-1]:
            raise ValueError

        if single.match(cmd).group(1) == 's':
            on = page_list.pages[page_list.cpage].select([int(sm.group(2))])
            page_list.selected.update(on)
        else:
            off = page_list.pages[page_list.cpage].deselect([int(sm.group(2))])
            page_list.selected.difference_update(off)
    
    elif batch.match(cmd):
        bm = batch.match(cmd)
        if (int(bm.group(2)) < page_list.itemno[0][0]
            or int(bm.group(3)) > page_list.itemno[-1][-1]
            or int(bm.group(2)) > int(bm.group(3))):
            raise ValueError

        target = set(range(int(bm.group(2)), int(bm.group(3)) + 1))
        if batch.match(cmd).group(1) == 's':
            for i, j in enumerate(page_list.itemno):
                on = page_list.pages[i].select(list(set(j) & target))
                page_list.selected.update(on)
        else:
            for i, j in enumerate(page_list.itemno):
                off = page_list.pages[i].deselect(list(set(j) & target))
                page_list.selected.difference_update(off)

    return True


def handle_update(page_list, cmd):
    valid = re.compile(r'[edvlariupcb]')
    m = valid.match(cmd)

    if not m:
        print("Unrecognized command.")
        time.sleep(0.5)

    elif cmd == 'e': # Enable
        pass

    elif cmd == 'd': # Disable
        pass

    elif cmd == 'v': # View info
        pass

    elif cmd == 'l': # List selected
        pass

    elif cmd == 'a': # Add metrics
        pass

    elif cmd == 'r': # Remove metrics
        pass

    elif cmd == 'i': # Change interval
        pass

    elif cmd == 'u': # Change pmproxy url
        pass

    elif cmd == 'p': # Change policy id
        pass

    elif cmd == 'c': # Create config file
        pass

    elif cmd == 'b': # Back to selection
        pass
