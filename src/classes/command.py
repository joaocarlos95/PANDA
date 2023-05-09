import inspect
import os
from datetime import date
from netmiko.utilities import get_structured_data
from OuiLookup import OuiLookup


class Command():

    def __init__(self, device, info, command, textfsm):
        self.device = device
        self.info = info
        self.command = command
        self.textfsm = textfsm
        self.output = None
        self.output_parsed = None
        self.status = None

    def get_mac_vendor(self):
        ''' Get MAC Address vendor from all devices connected to the switch '''

        for line in self.output_parsed:
            vendor = list(OuiLookup().query(line['destination_address'])[0].values())[0]
            print(vendor)
            line['vendor'] = vendor

    def run(self, config_mode=False, save_output=True):
        ''' Connect to a given device and run the requested command '''

        # Connection to the device couln't be made
        if self.device.connection == None: return
        # Reconnect to the device, since connection was closed
        elif not self.device.connection.is_alive(): self.device.connect()

        if self.info == 'Interfaces Counters':
            print('[>] Clearing counters and waiting 5 minutes...')
            #self.device.clear_counters()
            #time.sleep(300)

        try:
            # Apply configuration on the device, entering in configuration mode
            if config_mode:
                print(f"[>] Applying configuration: {self.command}")
                self.device.connection.config_mode()
                self.output = self.device.connection.send_config_set(self.command)
                self.device.connection.exit_config_mode()
            # Get configurations from the device
            else:
                print(f"[>] Getting configuration: {self.command}")
                if self.info == 'Configuration':
                    read_timeout = 600
                else:
                    read_timeout = 100
                self.output = self.device.connection.send_command(self.command, read_timeout=read_timeout)
                # Parse command output from the device
                if self.textfsm:
                    self.output_parsed = get_structured_data(self.output, \
                         platform=self.device.vendor_os, command=self.command)

                    if self.info == 'MAC Address Table':
                        self.get_mac_vendor()

            if 'Invalid input detected' in self.output:
                print(f"[!] Command not found: {self.command}")
                self.status = 'Command not found'
            elif type(self.output_parsed) == str and self.textfsm:
                print(f"[!] Error parsing the output of the command: {self.command}")
                self.status = 'Error parsing the output'
            else:
                self.status = ['Done']
           
        except Exception as exception:
            if 'Pattern not detected' in str(exception):
                print(f"[!] Pattern not detected on {self.device.ip_address} in command: {self.command}")
                self.status = f"Error getting information from command: {self.command}"
                return
            raise Exception(f"Error in {inspect.currentframe().f_code.co_name}", exception, self.device.ip_address)

    def save_output(self):
        ''' Save in a .txt file the output of the command issued on the device '''

        os.makedirs(f"{self.device.client.dir}/outputfiles/{self.info}", exist_ok=True)
        path = f"{self.device.client.dir}/outputfiles/{self.info}"
        
        current_datetime = date.today().strftime('%Y%m%d')
        command = self.command.replace(' ', '_').replace('/', '')
        filename = f"[{current_datetime}] {self.device.hostname} ({self.device.ip_address}) - {command}.txt"
        with open(f"{path}/{filename}", mode='w', encoding='utf-8') as file:
            file.write(f"{self.device.hostname}# {self.command}\n")
            file.write(self.output)
