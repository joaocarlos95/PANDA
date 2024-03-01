import os
import sys
import time
from flask import Flask, render_template, request, jsonify, Response

from src.classes.client import Client
from src.classes.colors import Colors


CLIENT_NAME = "ANA Aeroportos"
ROOT_DIRECTORY = "C:/Users/jlcosta/OneDrive - A2itwb Tecnologia S.A/01. Clientes/ANA Aeroportos/04. Automation"
CONFIG_OPTIONS = {
    'get_configs': {
        'Device': [
            {'id': 'Device Configuration', 'name': 'Device Configuration', 'label': 'Configuration', 'status': ''},
            {'id': 'Device Information', 'name': 'Device Information', 'label': 'Information', 'status': ''},
            {'id': 'Device Directory', 'name': 'Device Directory', 'label': 'Directory', 'status': 'disabled'},
            {'id': 'Device Management', 'name': 'Device Management', 'label': 'Management', 'status': ''},
            {'id': 'Device Licence', 'name': 'Device Licence', 'label': 'Licence', 'status': 'disabled'},
        ],
        'Interface': [
            {'id': 'Interface Statistics', 'name': 'Interface Statistics', 'label': 'Statistics', 'status': 'disabled'},
            {'id': 'Interface Information', 'name': 'Interface Information', 'label': 'Information', 'status': 'disabled'},
            {'id': 'Interface Status', 'name': 'Interface Status', 'label': 'Status', 'status': 'enable'},
        ],
        'Discovery Protocols': [
            {'id': 'Neighbors CDP', 'name': 'Neighbors CDP', 'label': 'Neighbors CDP', 'status': ''},
            {'id': 'Neighbors LLDP', 'name': 'Neighbors LLDP', 'label': 'Neighbors LLDP', 'status': ''},
            {'id': 'CDP Configuration', 'name': 'CDP Configuration', 'label': 'CDP Configuration', 'status': ''},
        ],
        'Network Diagram': [
            {'id': 'Network Diagram CDP', 'name': 'Network Diagram CDP', 'label': 'CDP Neighbors', 'status': ''},
            {'id': 'Network Diagram LLDP', 'name': 'Network Diagram LLDP', 'label': 'LLDP Neighbors', 'status': ''},
        ],
        'Others': [
            {'id': 'MAC Address Table', 'name': 'MAC Address Table', 'label': 'MAC Address Table', 'status': 'disabled'},
            {'id': 'Local Users', 'name': 'Local Users', 'label': 'Local Users', 'status': ''},
        ]
    },
    'set_configs': {
        'Authentication': [
            {'id': 'Device Management', 'name': 'Device Management', 'label': 'Management', 'status': 'disabled'},
            {'id': 'TACACS', 'name': 'TACACS', 'label': 'TACACS+', 'status': ''},
            {'id': 'Local_Users', 'name': 'Local_Users', 'label': 'Local Users', 'status': ''},
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
    return render_template('get_configs.html', config_options=CONFIG_OPTIONS['get_configs'], **template_context)

@app.route('/set_configs')
def set_configs():
    template_context = {}
    if CLIENT_NAME is not None:
        template_context['client_name'] = CLIENT_NAME
    if ROOT_DIRECTORY is not None:
        template_context['root_directory'] = ROOT_DIRECTORY
    return render_template('set_configs.html', config_options=CONFIG_OPTIONS['set_configs'], **template_context)

@app.route('/update_config_options', methods=['POST'])
def update_config_options():
    global CONFIG_OPTIONS
    config_options = request.json
    method = config_options.get('method')
    del config_options['method']
    CONFIG_OPTIONS[method] = config_options
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
            if option['status'] == 'checked':
                checked_options.append(option['id'])

    return checked_options


@app.route('/run_get_configs', methods=['POST'])
def run_get_configs():
    start_time = time.time()

    if ROOT_DIRECTORY == None or CLIENT_NAME == None:
        print(f"{Colors.NOK_RED}[>]{Colors.END} Please specify the Client Name and Root Directory in the proper forms")
        return Response(status=200)

    get_configs_info = get_checked_options(method='get_configs')

    # Create a new client object and initialize all data (command list)
    client = Client(ROOT_DIRECTORY, CLIENT_NAME)
    client.get_devices_from_csv()
    client.get_commands()

    # Get device information for each information requested
    client.get_concurrent_configs(get_configs_info=get_configs_info)

    # Generate script data, converting all class objects to nested dicts
    script_data = client.generate_data_dict()
    output_parsed = client.generate_config_parsed(script_data)

    # Generate diagrams using CDP or LLDP neighbors
    if 'Network Diagram CDP' in get_configs_info:
        graph = client.generate_graph(output_parsed=output_parsed, discovery_protocol='CDP')
        client.generate_diagram(graph)
    elif 'Network Diagram LLDP' in get_configs_info:
        graph = client.generate_graph(output_parsed=output_parsed, discovery_protocol='LLDP')
        client.generate_diagram(graph)
    
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


if __name__ == "__main__":
    app.run(debug=True)