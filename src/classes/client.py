import csv
import json
import os
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from getpass import getpass
from jinja2 import Environment, FileSystemLoader
from src.classes.decorators import write_to_file

import inspect
from datetime import date
from N2G import yed_diagram
from pykeepass import PyKeePass
from src.classes.device import Device
from src.classes.colors import Colors


MAX_WORKERS = 40


class Client:
    '''
    Class used to define client variables, which are used by other classes, and 
    to define the script main execution, namely import and export data.
    '''

    def __init__(self, dir, name, keepass=None, cmd_list=None, ftp_server=None):
        '''
        Constructor used to create a new client object, definig its main directory, name and
        threading lock to avoid race conditions when accessing multiple devices at the same time
        to perform operations.
        '''
        self.dir = dir
        self.name = name
        self.device_list = []
        self.keepass = keepass

        self.get_devices_from_csv()
        print(f"{Colors.OK_GREEN}[>]{Colors.END} Number of devices being interventioned: {len(self.device_list)}")

    def get_j2_template(self):
        '''
        Define the directory of jinja2 templates and specify the base template (skeleton) to be loaded
        The base_config.j2 template will then be extended by the child templates, specified by the 
        config_blocks variable passed in the constructor
        '''

        # Load the base template and assign it to a variable for further usage
        env = Environment(
            loader=FileSystemLoader(f"{os.path.dirname(__file__)}/../jinja2_templates"), 
            trim_blocks=True, 
            lstrip_blocks=True)
        self.j2_template = env.get_template('base_config.j2')

    def get_j2_data(self):
        '''
        Get the data to be used in the jinja2 template, from a YAML file
        '''

        # Open the default config_data.yaml file and load the content to a variable
        with open(f"{self.dir}/inputfiles/config_data.yaml") as file:
            self.j2_data = yaml.safe_load(file)

    def get_devices_from_csv(self):
        '''
        Get device list from .csv file and create a device object with the information
        collected from it. If a keepass database is used to obtain device credentials, this function
        will call the get_kdbx_credentials function to get the credentials.
        '''

        # Load client devices information from .csv file present in the client directory
        if os.path.exists(f"{self.dir}/inputfiles/device_list.csv"):
            path = f"{self.dir}/inputfiles/device_list.csv"
        # If this file is not present in the client directory, open the default one 
        else:
            path = f"{os.path.dirname(__file__)}/../inputfiles/device_list.csv"

        with open(path, mode='r', encoding='utf-8') as file:
            for row in csv.DictReader(file, skipinitialspace=True,):
                
                # Ignore devices commented
                if row['vendor_os'].startswith('#'):
                    continue
                else:
                    # Credentials in .csv file have higher priority than in keepass database
                    if row['username'] != '' and row['password'] != '':
                        credentials = {
                            'username': row['username'],
                            'password': row['password'],
                            'enable_secret': row['enable_secret']
                        }                   
                    # Check if keepass has device credentials
                    elif self.keepass:
                        try:
                            credentials = self.get_kdbx_credentials(row['ip_address'])
                        except Exception as exception:
                            raise exception
                    # Couldn't find credentials neither in .csv file nor .kdbx file
                    else:
                        credentials = {
                            'username': None,
                            'password': None,
                            'enable_secret': None
                        }

                # Create a new Device object and append it to the list of devices
                device = Device(self, row['vendor_os'], row['ip_address'], credentials)
                self.device_list.append(device)

    def get_kdbx_credentials(self, ip_address):
        '''
        Get device credentials from keepass database, specifying the client name and device
        IP address.
        '''
    
        try:
            # Load .kdbx file, passing in the argument the filename and respective password
            keepass_file = PyKeePass(**self.keepass)
        except Exception as exception:
            if 'No such file or directory:' in str(exception):
                print(f"{Colors.NOK_RED}[!]{Colors.END} Error getting keepass database)")
                raise Exception(f"{Colors.NOK_RED}[!]{Colors.END} Error getting keepass database)")
            elif len(str(exception)) == 0:
                print(f"{Colors.NOK_RED}[!]{Colors.END} Wrong keepass password")
                raise Exception(f"{Colors.NOK_RED}[!]{Colors.END} Wrong keepass password")
            else:
                raise Exception(f"{Colors.NOK_RED}[!]{Colors.END} Error in {inspect.currentframe().f_code.co_name}", exception)

        # Find client group within keepass, using its name
        group = keepass_file.find_groups(name=self.name, first=True)
        if not group:
            print(f"{Colors.NOK_RED}[!]{Colors.END} Group {self.name} doesn't exist in keepass database")
            raise Exception(f"{Colors.NOK_RED}[!]{Colors.END} Group {self.name} doesn't exist in keepass database")

        # Find device credentials, using its IP address 
        entry = keepass_file.find_entries(group=group, url=ip_address, tags=['SSH', 'Telnet'], recursive=True, first=True)
        if not entry:
            # Find device credentials, using common entry (usually credentials for all devices)
            entry = keepass_file.find_entries(group=group, title='RADIUS', first=True)
            if not entry:
                print(f"{Colors.NOK_RED}[!]{Colors.END} Couldn't find credentials for device with IP: {ip_address}")
                raise Exception(f"{Colors.NOK_RED}[!]{Colors.END} Couldn't find credentials for device with IP: {ip_address}")

        return {'username': entry.username, 'password': entry.password, 'enable_secret': None}


    def get_commands(self):
        '''
        Get list of all supported commands of this script to be used in GetConfigs.
        '''
        with open(f"{os.path.dirname(__file__)}/../commands.json", 'r', encoding='utf-8') as cmds:
            self.command_list = json.load(cmds)
        # Define environment variable for TextFSM, so that the package can get the correct templates
        os.environ['NET_TEXTFSM'] = os.path.join(os.path.dirname(__file__), '../../dep/ntc-templates/ntc_templates/templates')


    def get_concurrent_configs(self, get_configs_info: list) -> None:
        '''
        Function used to interact with the devices in a concurrent way (using concurrent.futures),
        takind advantage of threading to get information from the devices at the same time
        '''

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_list = [executor.submit(device.get_configs, get_configs_info) for device in self.device_list]
            for future in as_completed(future_list):
                future.result()

    def set_concurrent_configs(self, config_blocks: list) -> None:
        '''
        Function used to interact with the devices in a concurrent way (using concurrent.futures),
        takind advantage of threading to get information from the devices at the same time
        '''

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_list = [executor.submit(device.set_configs, config_blocks) for device in self.device_list]
            for future in as_completed(future_list):
                future.result()

    @write_to_file
    def generate_data_dict(self) -> dict:
        '''
        Generate a data structured with all the data used to interact with the devices and the 
        output of the interaction. Only the relevant data will be stored
        '''

        print(f"{Colors.OK_GREEN}[>]{Colors.END} Generating script output")

        # Transform client object in dict and remove unnecessary key/values
        client_dict = self.__dict__.copy()
        del client_dict['keepass']
        del client_dict['command_list']

        # Transform device objects in dict and remove unnecessary key/values
        device_list = []
        for device_obj in self.device_list:
            device_dict = device_obj.__dict__.copy()
            del device_dict['client']
            del device_dict['credentials']
            del device_dict['connection']

            # Transform config objects in dict and remove unnecessary key/values
            config_list = []
            for config_obj in device_obj.config_list:
                config_dict = config_obj.__dict__.copy()
                del config_dict['device']
                config_list.append(config_dict)

            # Replace the config object list by a config dict list
            device_dict['config_list'] = config_list
            device_list.append(device_dict)
        # Replace the device object list by a device dict list
        client_dict['device_list'] = device_list
        return client_dict

    @write_to_file
    def generate_config_parsed(self, script_data: dict) -> dict:
        '''
        Merge output parsed from TextFSM package from all devices in a single file
        '''

        print(f"{Colors.OK_GREEN}[>]{Colors.END} Merging output parsed")
        output_parsed_dict = {}

        for device in script_data['device_list']:
            merged_output = {
                'device_hostname': device['hostname'],
                'device_ip_address': device['ip_address']
            }
            for config in device['config_list']:
                config_info = config.get('info')
                output_parsed_list = []
                if config and len(config) > 0 and 'output_parsed' in config.keys() and config['output_parsed']:
                    for output_parsed in config['output_parsed']:
                        merged_output.update(output_parsed)
                        output_parsed_list.append(merged_output.copy())
                else:
                    output_parsed_list.append(merged_output)
            output_parsed_dict.setdefault(config_info, []).extend(output_parsed_list)

        return output_parsed_dict

    def generate_graph_from_cdp(self, output_parsed:dict) -> dict:
        '''
        Generate a dict variable representing network diagram based on neighbors adjancies
        '''

        graph = {'nodes': [], 'links': []}
        for entry in output_parsed['Network Diagram CDP']:
            device_ip_address = entry['device_ip_address'] if 'device_ip_address' in entry else ''
            device_hostname = entry['device_hostname'] if 'device_hostname' in entry else ''
            remote_ip_address = entry['remote_ip_address'] if 'remote_ip_address' in entry else ''
            remote_host = entry['remote_host'] if 'remote_host' in entry else ''
            local_port = entry['local_port'] if 'local_port' in entry else ''
            remote_port = entry['remote_port'] if 'remote_port' in entry else ''

            graph['nodes'].append({
                'id': remote_ip_address,
                'top_label': remote_host,
                'bottom_label': remote_ip_address
            })
            graph['links'].append({
                'source': device_ip_address, 
                'target': remote_ip_address,
                'src_label':local_port,
                'trgt_label': remote_port
            })
        graph['nodes'].append({
            'id': device_ip_address,
            'top_label': device_hostname,
            'bottom_label': device_ip_address
        })

        return graph

    @write_to_file
    def generate_diagram(self, graph):
        '''
        Generate network diagram in drawio format, based on neighbors adjancies
        '''

        print(f"{Colors.OK_GREEN}[>]{Colors.END} Generating Network Diagram")
        diagram = yed_diagram()
        diagram.from_dict(graph)
        diagram.layout(algo='tree')

        return diagram












    def generate_config_report(self):
        ''' Generate report for commands executed on the device'''

        print('[>] Generating configuration report')
        report = []
        for device in self.report:
            # For each command runned on a device, create a new .csv row
            if device['command_list'] == []:
                report.append({
                    'device_hostname': device['hostname'],
                    'device_ip_address': device['ip_address'],
                    'info': '',
                    'command': '',
                    'status': device['status']
                })
            for command in device['command_list']:
                if command['status'] == None:
                    status = device['status']
                else:
                    status = command['status']
                report.append({
                    'device_hostname': device['hostname'],
                    'device_ip_address': device['ip_address'],
                    'info': command['info'],
                    'command': command['command'],
                    'status': status
                })

        self.write_csv(report, filename='Configuration Report')

    def generate_upgrade_report(self):
        ''' Generate report for devices upgrade process '''

        print('[>] Generating upgrade report')
        report = []
        for device in self.report:
            # For each command runned on the device, create a new .csv row
            for upgrade in device['upgrade_list']:

                # Authentication to the device failed
                if 'Authentication failed' in upgrade['status']:
                    current_release = None
                # Devices with success login
                else:
                    current_release = upgrade['current_release']['version']
                
                # Devices not in scope
                if upgrade['target_release'] == None:
                    target_release = None
                # Devices in scope
                else:
                    target_release = upgrade['target_release']['version']
                
                report.append({
                    'device_hostname': device['hostname'],
                    'device_ip_address': device['ip_address'],
                    'step': upgrade['step'],
                    'current_release': current_release,
                    'target_release': target_release,
                    'status': upgrade['status']
                })

        self.write_csv(report, filename='Upgrade Report')