import os
import time
import yaml
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, Response
from nornir.core.filter import F

from src.classes.client import Client
from src.classes.colors import Colors


CLIENT_NAME = "ANA Aeroportos"
ROOT_DIRECTORY = "C:/Users/jlcosta/OneDrive - A2itwb Tecnologia S.A/01. Clientes/ANA Aeroportos/04. Automation"
CONFIG_OPTIONS = {
    'set_configs': {
        'Authentication': [
            {'id': 'Device Management', 'name': 'Device Management', 'label': 'Management', 'status': ''},
            {'id': 'TACACS', 'name': 'TACACS', 'label': 'TACACS+', 'status': ''},
        ],
        'VLAN': [
            {'id': 'VLAN', 'name': 'VLAN', 'label': 'VLAN', 'status': ''},
        ],
        'Interfaces': [
            {'id': 'Ports', 'name': 'Ports', 'label': 'Ports', 'status': ''},
        ],
        'Discovery Protocols': [
            {'id': 'CDP', 'name': 'CDP', 'label': 'CDP', 'status': ''},
            {'id': 'LLDP', 'name': 'LLDP', 'label': 'LLDP', 'status': ''},
        ],
        'Monitoring': [
            {'id': 'SNMP', 'name': 'SNMP', 'label': 'SNMP', 'status': ''},
        ],
        'Others': [
            {'id': 'General', 'name': 'General', 'label': 'General', 'status': ''},
        ]
    }
}


app = Flask(__name__, template_folder='src/web/templates', static_folder='dep/')

@app.route('/')
def index():
    template_context = {}
    if CLIENT_NAME is not None:
        template_context['client_name'] = CLIENT_NAME
    if ROOT_DIRECTORY is not None:
        template_context['root_directory'] = ROOT_DIRECTORY
    return render_template('index.html', **template_context)

@app.route('/get_configs')
def get_configs():
    template_context = {}
    if CLIENT_NAME is not None:
        template_context['client_name'] = CLIENT_NAME
    if ROOT_DIRECTORY is not None:
        template_context['root_directory'] = ROOT_DIRECTORY
    return render_template('get_configs.html', config_options=CONFIG_OPTIONS['get_configs'], device_groups=CLIENT.nornir.inventory.groups, **template_context)

@app.route('/set_configs')
def set_configs():
    template_context = {}
    if CLIENT_NAME is not None:
        template_context['client_name'] = CLIENT_NAME
    if ROOT_DIRECTORY is not None:
        template_context['root_directory'] = ROOT_DIRECTORY
    return render_template('set_configs.html', config_options=CONFIG_OPTIONS['set_configs'], **template_context)

@app.route('/generate_configs')
def generate_configs():
    template_context = {}
    if CLIENT_NAME is not None:
        template_context['client_name'] = CLIENT_NAME
    if ROOT_DIRECTORY is not None:
        template_context['root_directory'] = ROOT_DIRECTORY
    return render_template('generate_configs.html', config_options=CONFIG_OPTIONS['set_configs'], **template_context)

@app.route('/update_device_group_options', methods=['POST'])
def update_device_group_options():
    global CONFIG_OPTIONS
    CONFIG_OPTIONS['device_group'] = request.json.get('device_group_options')
    return jsonify(success=True)

@app.route('/update_client_name', methods=['POST'])
def update_client_name():
    global CLIENT_NAME
    CLIENT_NAME = request.form.get('client_name')
    return CLIENT_NAME

@app.route('/update_root_directory', methods=['POST'])
def update_root_directory():
    global ROOT_DIRECTORY
    ROOT_DIRECTORY = request.form.get('root_directory')
    return ROOT_DIRECTORY


def get_checked_options(method: str):
    checked_options = []
    for category, options in CONFIG_OPTIONS[method].items():
        for option in options:
            if option['status'] == 'checked' and method == 'get_configs':
                checked_options.append(option['id'])
            elif option['status'] == 'checked' and method == 'set_configs':
                checked_options.append(option['id'])

    return checked_options


@app.route('/run_get_configs', methods=['POST'])
def run_get_configs():
    start_time = time.time()

    selected_data = request.get_json()
    get_configs_info = selected_data['informationDataSelected']

    selected_groups = selected_data['selectedDeviceGroups']
    nornir_group_filter = F(groups__contains=selected_groups[0])
    for group in selected_groups[1:]:
        nornir_group_filter |= F(groups__contains=group)
   
    nornir_filtered = CLIENT.nornir.filter(nornir_group_filter)
    CLIENT.nornir_get_configs(get_configs_info=get_configs_info, nornir_filtered=nornir_filtered)

    script_data = CLIENT.nornir_generate_data_dict()
    output_parsed = CLIENT.nornir_generate_config_parsed(script_data)

    # Generate diagrams using CDP or LLDP neighbors
    # if 'Network Diagram CDP' in get_configs_info:
    #     graph = CLIENT.generate_graph(output_parsed=output_parsed, discovery_protocol='CDP')
    #     CLIENT.generate_diagram(graph)
    # elif 'Network Diagram LLDP' in get_configs_info:
    #     graph = CLIENT.generate_graph(output_parsed=output_parsed, discovery_protocol='LLDP')
    #     CLIENT.generate_diagram(graph)
    
    print(f"{Colors.OK_GREEN}[>]{Colors.END} Execution time: {time.time() - start_time} seconds")
    return Response(status=204)


@app.route('/run_set_configs', methods=['POST'])
def run_set_configs():
    start_time = time.time()

    if ROOT_DIRECTORY == None or CLIENT_NAME == None:
        print(f"{Colors.NOK_RED}[>]{Colors.END} Please specify the Client Name and Root Directory in the proper forms")
        return Response(status=200)

    config_blocks = get_checked_options(method='set_configs')

    # Create a new client object and initialize all data (command list)
    client = Client(ROOT_DIRECTORY, CLIENT_NAME)
    client.get_devices_from_csv()
    client.get_j2_template()
    client.get_j2_data()

    # Get device information for each information requested
    client.set_concurrent_configs(config_blocks=config_blocks)

    # Generate script data, converting all class objects to nested dicts
    # script_data = client.generate_data_dict()
    # output_parsed = client.generate_config_parsed(script_data)

    print(f"{Colors.OK_GREEN}[>]{Colors.END} Execution time: {time.time() - start_time} seconds")
    return Response(status=204)


def init_config_options() -> None:
    '''
    Initialize global CONFIG_OPTIONS with the configuration options
    from the config.yaml file. This function is used to populate the website
    with the available options.

    The options are grouped by their respective group, which is defined in the
    config.yaml file.
    '''

    global CONFIG_OPTIONS

    with open(f"{os.path.dirname(__file__)}/src/config.yaml", 'r') as nornir_config:
        config = yaml.safe_load(nornir_config)

        get_configs = defaultdict(list)
        # Iterate through all the user-defined options in the config.yaml file
        for key, value in config['user_defined']['PANDA_data'].items():
            # Append the current option to the corresponding group
            get_configs[value['group']].append({
                # ID, Name and Label of the option are the same
                'id': key,
                'name': key,
                'label': value['label'],
                'status': value['status']
            })

    CONFIG_OPTIONS['get_configs'] = dict(get_configs)


def init_client() -> None:
    ''' '''
    global CLIENT

    if ROOT_DIRECTORY == None or CLIENT_NAME == None:
        print(f"{Colors.NOK_RED}[>]{Colors.END} Please specify the Client Name and Root Directory in the proper forms")
        return Response(status=200)

    CLIENT = Client(ROOT_DIRECTORY, CLIENT_NAME)


if __name__ == "__main__":

    init_config_options()
    init_client()
    app.run(debug=True)