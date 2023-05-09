# -*- coding: UTF-8 -*-

import inspect
import json
import os
import sys
import time
from multiprocessing import Manager, Process
from classes import Client
from getpass import getpass
from src.classes.client import Client as NC
from src.classes.colors import Colors


def raise_exception(exception: str) -> None:
    sys.exit(f"{Colors.NOK_RED} {exception}")


if __name__ == '__main__':
    start_time = time.time()
    validations = {'yes': True, 'y': True, 'no': False, 'n': False}

    with open(os.path.join(os.path.dirname(__file__), './get_configs.txt'), 'r', encoding='utf-8') as file:     
        get_configs_info = []
        keepass = None

        for line in file:
            if 'Root Directory:' in line:
                line = file.readline()
                root_dir = line.split('>')[1].strip() if '>' in line and len(set(line)) > 2 else raise_exception('Root directory not specified')
            elif 'Client Name:' in line:
                line = file.readline()
                client_name = line.split('>')[1].strip() if '>' in line and len(set(line)) > 2 else raise_exception('Client name not specified')
            elif 'Keepass Database:' in line:
                line = file.readline()
                if '>' in line and len(set(line)) > 2 and '.kdbx' in line:
                    keepass = {
                        'filename': line.split('>')[1].strip(),
                        'password': getpass(f"{Colors.OK_YELLOW}[>]{Colors.END} Please insert your Keepass password: ")
                    }
            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip()
                get_configs_info.append(info_requested)
                # if info_requested == 'Interfaces Counters':
                #     while True:
                #         try:
                #             to_clear = validations[input(f"{Colors.OK_YELLOW}{Colors.END} Please confirm if you want to clear the counters (Yes or No): ").lower()]
                #             command_list['Interfaces Counters']['clear_counters']['to_clear'] = to_clear
                #             break
                #         except KeyError:
                #             print(f"{Colors.NOK_RED}{Colors.END} Please answer with Yes or No.")

    # Confirm the information to be requested to the devices
    print(f"{Colors.OK_YELLOW}[>]{Colors.END} Please confirm the following information to be gathered (Yes or No):")
    for info_requested in get_configs_info:
        print(f"       > {info_requested}")
    while True:
        try:
            if validations[input(f"    {Colors.WHITE_UNDER}Answer{Colors.END}: ").lower()]:
                break
            else:
                print(f"{Colors.NOK_RED}{Colors.END} Please select the proper information to be gathered and repeat.")
                sys.exit()
        except KeyError:
            print(f"{Colors.NOK_RED}{Colors.END} Please answer with Yes or No.")

    # Create a new client object
    client = NC(root_dir, client_name, keepass=keepass)

    # Initialize all data (command list)
    client.get_commands()

    # Get device information for each information requested
    client.get_concurrent_configs(get_configs_info=get_configs_info)

    # Generate script data, converting all class objects to nested dicts
    script_data = client.generate_data_dict()
    output_parsed_dict = client.generate_config_parsed(script_data)

    if 'Network Diagram' in get_configs_info:
        graph = client.generate_graph(output_parsed_dict)
        # client.generate_diagram(graph)
    

    print(f"{Colors.OK_GREEN}[>]{Colors.END} Execution time: {time.time() - start_time} seconds")
