# -*- coding: UTF-8 -*-

import os
import sys
import time
from getpass import getpass
from multiprocessing import Manager, Process
from src.classes.client import Client
from src.classes.colors import Colors


def raise_exception(exception: str) -> None:
    sys.exit(f"{Colors.NOK_RED} {exception}")


if __name__ == '__main__':
    start_time = time.time()
    validations = {'yes': True, 'y': True, 'no': False, 'n': False}

    with open(os.path.join(os.path.dirname(__file__), './set_configs.txt'), 'r', encoding='utf-8') as file:     
        config_blocks = []
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
                        'password': getpass(f"{Colors.OK_YELLOW}{Colors.END} Please insert your Keepass password: ")
                    }
            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip().lower().replace(" ", "_")
                config_blocks.append(info_requested)

    # Confirm the configurations to be generated and applied to the devices
    print(f"{Colors.OK_YELLOW}{Colors.END} Please confirm the following configuration blocks (Yes or No): ")
    for info_requested in config_blocks:
        print(f"       > {info_requested}")
    while True:
        try:
            if validations[input('    Answear: ').lower()]:
                break
            else:
                print(f"{Colors.NOK_RED}{Colors.END} Please select the proper configuration blocks.")
                sys.exit()
        except KeyError:
            print(f"{Colors.NOK_RED}{Colors.END} Please answer with Yes or No.")

    # Create a new client object
    client = Client(root_dir, client_name, keepass=keepass)

    # Initialize all data (templates, templates data)
    client.get_j2_template()
    client.get_j2_data()
    
    # Generate and apply the configuration for each device
    [device.set_configs(config_blocks) for device in client.device_list]

    #process_list = [Process(target=device.set_configs, args=(config_blocks)) for device in client.device_list]
    #[process.start() for process in process_list]
    #[process.join() for process in process_list]
    
    # client.report = report
    # client.generate_config_report()
    # client.generate_config_parsed()

    # with open(f"{client.dir}/outputfiles/script_output_set.json", 'w') as outfile:
    #     json.dump(list(report), outfile, indent=2)

    print(f"Execution time: {time.time() - start_time} seconds")
