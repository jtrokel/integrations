import constants
from utils import api_utils, file_utils

def create_integrations(node, key, url):
    hostname = node['hostname']
    
    for group in node['groups']:
        headers = { 
            "Authorization": f"ApiKey {key}",
            "Content-Type": "application/json",
            "kbn-xsrf": "exists"
        }

        body = {
            "policy_id": f"{group['policy_id']}",
            "package": {
                'name': 'httpjson',
                'version': '1.20.0',
            },
            "name": f"pcp-{hostname}-{group['interval']}",
            "description": f"Collect PCP metrics from {hostname} every {group['interval']}",
            "namespace": "default",
            "inputs": {
                "generic-httpjson": {
                    "enabled": True,
                    "streams": {
                        "httpjson.generic": {
                            "enabled": True,
                            "vars": {
                                "data_stream.dataset": "httpjson.pcp",
                                "pipeline": "pmwebapi-parser",
                                "request_url": f"{group['pmproxy_url']}pmapi/fetch?hostspec={hostname}.lle.rochester.edu&client={hostname}.lle.rochester.edu&names={group['metrics']}",
                                "request_interval": f"{group['interval']}",
                                "request_method": "GET",
                                "request_redirect_headers_ban_list": [],
                                "oauth_scopes": [],
                                "tags": [
                                    "forwarded"
                                ]
                            }
                        }
                    }
                }
            }
        }

        print("Sending request")
        response = requests.post(f"{url}api/fleet/package_policies", headers=headers, json=body)
        
        if response.status_code == 409:
            print(response.text)


def iter_nodes(conf, args):
    i = 1
    for node in conf['nodes']:
        print(f"Creating integrations for node {i} of {len(conf['nodes'])} ({node['hostname']})")
        i += 1

        hostname = node['hostname']
        for group in node['groups']:
            group['hostname'] = hostname
            req = api_utils.build_request(conf, constants.CREATE, group)
            api_utils.request(req, args)


def create(args):
    config = file_utils.load_file(args.file)
    if args.check_config:
        file_utils.check_conf(config, constants.CREATE)

    api_utils.validate_key(config['api_key'], config['kibana_url'])

    iter_nodes(config, args)

