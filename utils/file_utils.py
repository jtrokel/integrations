import json

def load_file(infile):
    with open(infile) as f:
        try:
            config = json.load(f)
            return config
        except json.decoder.JSONDecodeError:
            print(f"Failed to parse JSON in {infile}. Ensure that it contains valid JSON.")
            exit(1)


def cc_helper(conf, expected):
    for k, v in expected.items():
        if isinstance(v, type):
            # Ensure conf has expected key and correct type for that key's value

            if k not in conf:
                return (False, f"Expected to find key {k} but did not.")
            if not isinstance(conf[k], v):
                return (False, f"Expected key {k} to have type {v.__name__}, but it had type {type(conf[k]).__name__}.")
        
        elif isinstance(v, dict):
            # Ensure conf has expected nested dictionary key and that key maps to a dict, and
            # Recursively check the nested dictionary

            if k not in conf:
                return (False, f"Expected to find key {k} but did not.")
            if not isinstance(conf[k], dict):
                return (False, f"Expected key {k} to have type dict, but it had type {type(conf[k]).__name__}.")
            
            subcheck = cc_helper(conf[k], v)
            if not subcheck[0]: # Sub-dictionary had an issue
                return (subcheck[0], f"Under {k}: {subcheck[1]}")

        elif isinstance(v, list):
            # Ensure conf has expected list key and that key maps to a list, and
            # Iteratively check each item in the list

            if k not in conf:
                return (False, f"Expected to find key {k} but did not.")
            if not isinstance(conf[k], list):
                return (False, f"Expected key {k} to have type list, but it had type {type(conf[k]).__name__}.")

            i = 0
            for item in conf[k]:
                # Assuming each item in the list has the same structure
                subcheck = cc_helper(item, v[0])
                if not subcheck[0]:
                    return (subcheck[0], f"Element {i} in {k}: {subcheck[1]}")
                i += 1

    # Everything looks good
    return (True, "Config file is structured correctly.") 


def check_conf(config, mode):
    ccs = {
        'create': {
            "api_key": str,
            "kibana_url": str,
            "nodes": [{
                "hostname": str,
                "groups": [{
                    "policy_id": str,
                    "pmproxy_url": str,
                    "interval": str,
                    "metrics": str
                }]
            }]
        },
        'view':   {},
        'delete': {}
    } 

    check = cc_helper(config, ccs[mode])

    print(check[1])
    exit(1) if not check[0] else exit(0)

