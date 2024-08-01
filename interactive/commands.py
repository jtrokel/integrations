import re
import time

from interactive import renderer, classes


def done():
    raise classes.ExitException


def search(page_list):
    search = input("\033[1m\033[32mSearch\033[0m>> ")
    page_list.clear_lines += 1
    new_lines = []
    for page in page_list.pages:
        for line in page.lines:
            if re.search(search, line):
                new_lines.append(line)

    if not new_lines:
        print("Search matched nothing.")
        time.sleep(0.5)
        return

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


def next_page(page_list):
    if page_list.cpage >= page_list.npages - 1:
        print("At last page already.")
        page_list.clear_lines += 1
        time.sleep(0.5)
    else:
        page_list.cpage += 1


def prev_page(page_list):
    if page_list.cpage <= 0:
        print("At first page already.")
        page_list.clear_lines += 1
        time.sleep(0.5)
    else:
        page_list.cpage -= 1


def jump_to(page_list, cmd):
    jump = re.compile(r'(\d+)j')
    jmp = jump.match(cmd)
    jtarget = int(jmp.group(1))
    if jtarget < 1 or jtarget > page_list.npages:
        print("Invalid page number.")
        time.sleep(0.5)
    else:
        page_list.cpage = jtarget - 1


def select_all(page_list):
    for i, j in enumerate(page_list.itemno):
        on = page_list.pages[i].select(list(j))
        page_list.selected.update(on)


def deselect_all(page_list):
    for i, j in enumerate(page_list.itemno):
        off = page_list.pages[i].deselect(list(j))
        page_list.selected.difference_update(off)


def single_item(page_list, cmd):
    single = re.compile(r'([sd])(\d+)$')
    sm = single.match(cmd)
    if not page_list.itemno[page_list.cpage][0] <= int(sm.group(2)) <= page_list.itemno[page_list.cpage][-1]:
        print("Item not on page.")
        time.sleep(0.5)
        return

    if single.match(cmd).group(1) == 's':
        on = page_list.pages[page_list.cpage].select([int(sm.group(2))])
        page_list.selected.update(on)
    else:
        off = page_list.pages[page_list.cpage].deselect([int(sm.group(2))])
        page_list.selected.difference_update(off)


def batch_items(page_list, cmd):
    batch = re.compile(r'([sd])(\d+)-(\d+)')
    bm = batch.match(cmd)
    if (int(bm.group(2)) < page_list.itemno[0][0]
        or int(bm.group(3)) > page_list.itemno[-1][-1]):
        print("Item index out of bounds.")
        time.sleep(0.5)
        return

    if int(bm.group(2)) > int(bm.group(3)):
        print("First index must be smaller than second.")
        time.sleep(0.5)
        return

    target = set(range(int(bm.group(2)), int(bm.group(3)) + 1))
    if batch.match(cmd).group(1) == 's':
        for i, j in enumerate(page_list.itemno):
            on = page_list.pages[i].select(list(set(j) & target))
            page_list.selected.update(on)
    else:
        for i, j in enumerate(page_list.itemno):
            off = page_list.pages[i].deselect(list(set(j) & target))
            page_list.selected.difference_update(off)


def handle_select(page_list, cmd):
    COMMANDS = {
        r'b': (done, ()),
        r'f': (search, ('page_list',)),
        r'n': (next_page, ('page_list',)),
        r'p': (prev_page, ('page_list',)),
        r'\d+j': (jump_to, ('page_list', 'cmd')),
        r'sa': (select_all, ('page_list',)),
        r'da': (deselect_all, ('page_list',)),
        r'[sd]\d+$': (single_item, ('page_list', 'cmd')),
        r'[sd]\d+-\d+': (batch_items, ('page_list', 'cmd'))
    }

    valid = re.compile(r'[npfb]|(s|d)(a|\d+|\d+-\d+)|\d+j')
    single = re.compile(r'([sd])(\d+)$')
    batch = re.compile(r'([sd])(\d+)-(\d+)')
    jump = re.compile(r'(\d+)j')
    m = valid.match(cmd)

    if not m:
        print("Unrecognized command.")
        time.sleep(0.5)
        page_list.clear_lines += 1
        return

    for (pattern, (func, param_types)) in COMMANDS.items():
        match = re.match(pattern, cmd)
        if match:
            params = []
            for ptype in param_types:
                if ptype == 'page_list':
                    params.append(page_list)
                elif ptype == 'cmd':
                    params.append(cmd)
            func(*params)


def enable(req_bodies, applied):
    try:
        for body in req_bodies:
            for inp in body['inputs']:
                body['inputs'][inp]['enabled'] = True
                for stream in body['inputs'][inp]['streams']:
                    body['inputs'][inp]['streams'][stream]['enabled'] = True
        return False
    except Exception as e:
        print(e)
        return applied


def disable(req_bodies, applied):
    try:
        for body in req_bodies:
            for inp in body['inputs']:
                body['inputs'][inp]['enabled'] = False
                for stream in body['inputs'][inp]['streams']:
                    body['inputs'][inp]['streams'][stream]['enabled'] = False
        return False
    except Exception as e:
        print(e)
        return applied


def view(selected, name_map, applied):
    url = re.compile(r'^http:\/\/(.*?)\/pmapi\/fetch\?hostspec=(.*?)&.*&names=(.*)$')
    print("\033[1mNon-Metric Info\033[0m")
    print(f"{'Integration':<22} | {'Host':<15}{'Enabled':<10}{'Interval':<10}{'pmproxy URL':<40}{'Policy ID'}")
    print('-' * 23 + '|' + '-' * 106)
    for integration in selected:
        body = transform_body(name_map[integration])
        for inp in body['inputs']:
            for stream in body['inputs'][inp]['streams']:
                match = url.match(body['inputs'][inp]['streams'][stream]['vars']['request_url'])
                host = match.group(2).split('.')[0]
                enabled = body['inputs'][inp]['enabled'] and body['inputs'][inp]['streams'][stream]['enabled']
                interval = body['inputs'][inp]['streams'][stream]['vars']['request_interval']
                pmproxy_url = match.group(1)
                policy_id = body['policy_id']
                # Can't get enabled to print 'true' and 'false'
                enabled = "True" if enabled else "False"
                print(f"{integration:<22} | {host:<15}{enabled:<10}{interval:<10}{pmproxy_url:<40}{policy_id}")

    print("\n\033[1mMetric Info\033[0m")
    for integration in selected:
        body = transform_body(name_map[integration])
        for inp in body['inputs']:
            for stream in body['inputs'][inp]['streams']:
                match = url.match(body['inputs'][inp]['streams'][stream]['vars']['request_url'])
                metrics = match.group(3)
                print(f"{f'{integration}:':<22}{metrics}\n")

    return applied

def quit(applied):
    if not applied:
        cont = input("You have updates that have not been applied. Are you sure you want to quit? (y/N): ")
        if cont != 'y':
            return applied

    raise classes.ExitException


def save(req_bodies, applied):
    pass


def add_metrics(req_bodies, applied):
    pass


def remove_metrics(req_bodies, applied):
    pass


def change_interval(req_bodies, applied):
    pass


def change_url(req_bodies, applied):
    pass


def see_updates(selected, name_map, req_bodies, applied):
    def color_wrap(color_code, string):
        return f"\033[{color_code}m{string}\033[0m"

    url = re.compile(r'^http:\/\/(.*?)\/pmapi\/fetch\?hostspec=(.*?)&.*&names=(.*)$')
    print("\nChanged fields are shown in \033[35mmagenta\033[0m, additions are shown in \033[32mgreen\033[0m, and removals are shown in \033[31mred\033[0m.")
    print("\033[1mNon-Metric Info\033[0m")
    print(f"{'Integration':<22} | {'Host':<15}{'Enabled':<10}{'Interval':<10}{'pmproxy URL':<40}{'Policy ID'}")
    print('-' * 23 + '|' + '-' * 106)
    for integration in selected:
        old_body = transform_body(name_map[integration])
        new_body = [d for d in req_bodies if d['name'] == old_body['name']][0]
        for inp in old_body['inputs']:
            for stream in old_body['inputs'][inp]['streams']:
    
                eshift = 10
                ishift = 10
                ushift = 40

                match = url.match(old_body['inputs'][inp]['streams'][stream]['vars']['request_url'])
                new_match = url.match(new_body['inputs'][inp]['streams'][stream]['vars']['request_url'])

                host = match.group(2).split('.')[0]
                new_host = new_match.group(2).split('.')[0]
                if host != new_host:
                    new_host = color_wrap('35', new_host)

                enabled = old_body['inputs'][inp]['enabled'] and old_body['inputs'][inp]['streams'][stream]['enabled']
                new_enabled = new_body['inputs'][inp]['enabled'] and new_body['inputs'][inp]['streams'][stream]['enabled']
                # Can't get enabled to print 'true' and 'false'
                enabled = "True" if enabled else "False"
                new_enabled = "True" if new_enabled else "False"
                if enabled != new_enabled:
                    new_enabled = color_wrap('35', new_enabled)
                    eshift += 9

                interval = old_body['inputs'][inp]['streams'][stream]['vars']['request_interval']
                new_interval = new_body['inputs'][inp]['streams'][stream]['vars']['request_interval']
                if interval != new_interval:
                    new_interval = color_wrap('35', new_interval)
                    ishift += 9

                pmproxy_url = match.group(1)
                new_pmproxy_url = new_match.group(1)
                if pmproxy_url != new_pmproxy_url:
                    new_pmproxy_url = color_wrap('35', new_pmproxy_url)
                    ushift += 9

                policy_id = old_body['policy_id']
                new_policy_id = new_body['policy_id']
                if policy_id != new_policy_id:
                    new_policy_id = color_wrap('35', new_policy_id)

                print(f"{integration:<22} | {new_host:<15}{new_enabled:<{eshift}}{new_interval:<{ishift}}{new_pmproxy_url:<{ushift}}{new_policy_id}")

    print("\n\033[1mMetric Info\033[0m")
    for integration in selected:
        old_body = transform_body(name_map[integration])
        new_body = [d for d in req_bodies if d['name'] == old_body['name']][0]
        for inp in old_body['inputs']:
            for stream in old_body['inputs'][inp]['streams']:
                old_match = url.match(old_body['inputs'][inp]['streams'][stream]['vars']['request_url'])
                new_match = url.match(new_body['inputs'][inp]['streams'][stream]['vars']['request_url'])
                old_metrics = old_match.group(3)
                new_metrics = new_match.group(3)

                out = ""
                if old_metrics == new_metrics:
                    out = "No change in metrics."
                    print(f"{f'{integration}:':<22}{out}\n")
                else:
                    old_list = old_metrics.split(',')
                    new_list = new_metrics.split(',')
                    s_added = set(new_list) - set(old_list)
                    s_removed = set(old_list) - set(new_list)
                    # To keep nice ordering:
                    added = [metric for metric in new_list if metric in s_added]
                    removed = [metric for metric in old_list if metric in s_removed]
                    o_added = color_wrap('32', ','.join(added))
                    o_removed = color_wrap('31', ','.join(removed))
                    print(f"{f'{integration}: ':<25}{color_wrap('32', '+')} {o_added}")
                    print(f"{'':<25}{color_wrap('31', '-')} {o_removed}")

    return applied


def create_config(req_bodies, applied):
    pass


def transform_body(old_body):
    good_keys = ['package', 'name', 'namespace', 'description', 'policy_id', 'vars']
    new_body = {key: old_body[key] for key in good_keys}
    
    new_body['package'].pop('title', '')
    
    # Transform inputs
    inputs = old_body['inputs']
    transformed_inputs = {}

    for input_item in inputs:
        input_type = input_item['type']
        policy_template = input_item['policy_template']
        streams = input_item['streams']

        transformed_inputs[f"{policy_template}-{input_type}"] = {
            'enabled': input_item['enabled'],
            'streams': {}
        }

        for stream in streams:
            stream_data_stream = stream['data_stream']
            stream_vars = stream['vars']
            stream_vars_transformed = {k: v['value'] for k, v in stream_vars.items() if 'value' in v}
            
            transformed_inputs[f'{policy_template}-{input_type}']['streams'][stream_data_stream['dataset']] = {
                'enabled': stream['enabled'],
                'vars': stream_vars_transformed
            }

    new_body['inputs'] = transformed_inputs
    return new_body


def handle_update(selected, name_map, req_bodies, cmd, applied):
    COMMANDS = {
        'e': (enable, ('req_bodies', 'applied')),
        'd': (disable, ('req_bodies', 'applied')),
        'v': (view, ('selected', 'name_map', 'applied')),
        'q': (quit, ('applied',)),
        's': (save, ('req_bodies', 'applied')),
        'a': (add_metrics, ('req_bodies', 'applied')),
        'r': (remove_metrics, ('req_bodies', 'applied')),
        'i': (change_interval, ('req_bodies', 'applied')),
        'u': (change_url, ('req_bodies', 'applied')),
        't': (see_updates, ('selected', 'name_map', 'req_bodies', 'applied')),
        'c': (create_config, ('req_bodies', 'applied'))
    }

    for (command, (func, param_types)) in COMMANDS.items():
        if cmd == command:
            params = []
            for ptype in param_types:
                if ptype == 'selected':
                    params.append(selected)
                elif ptype == 'name_map':
                    params.append(name_map)
                elif ptype == 'req_bodies':
                    params.append(req_bodies)
                elif ptype == 'applied':
                    params.append(applied)
            return func(*params)

    valid = re.compile(r'[edvqariutcbs]')
    m = valid.match(cmd)

    if not m:
        print("Unrecognized command.")
        time.sleep(0.5)
        return applied
