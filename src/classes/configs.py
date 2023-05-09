from datetime import datetime
from netmiko.utilities import get_structured_data
from OuiLookup import OuiLookup
from src.classes.colors import Colors 
from src.classes.decorators import write_to_file

class Configs:
    '''
    TBD
    '''

    def __init__(self, device, info: str) -> None:
        '''
        Constructor used to create a new object in the super class. This object interacts directly
        with the devices and serves both GetConfigs and SetConfigs purposes.
        '''
        self.device = device
        self.info = info

 
class SetConfigs(Configs):
    '''
    Class used to generate device configurations based on pre-defined templates and data 
    '''

    def __init__(self, device, info: str='apply_config') -> None:
        '''
        Constructor used to create a new object, passing to the super class the device object,
        used to interact with the devices
        '''
        super().__init__(device, info)

    @write_to_file
    def render_template(self, config_blocks: list) -> str:
        '''
        Generate device configuration, given a jinnja2 template and a YAML data file. This function
        receives as input a list of configuration blocks for the jinja2 template choose the child
        templates accordingly 
        '''

        data = {
            "config_blocks": config_blocks,
            "vendor_os": self.device.vendor_os,
            "ip_address": self.device.ip_address,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            **self.device.client.j2_data
        }
        
        self.config = self.device.client.j2_template.render(data)
        return self.config

    ### TO BE DONE: Check if configuration was successfully applied to the device
    @write_to_file
    def send_config(self, data: str) -> str:
        '''
        Send new configurations to the device, in a text format. The function will then split the
        text configuration into a list of commands.
        '''

        # Connection to the device couln't be made
        if self.device.connection == None:
            print(f"{Colors.NOK_RED}[{self.device.ip_address}]{Colors.END} Connection to the device couln't be made")
            raise Exception(f"[{self.device.ip_address}] Connection to the device couln't be made")
        # Reconnect to the device, since connection was closed
        elif not self.device.connection.is_alive():
            self.device.connect()
            print(f"{Colors.OK_YELLOW}[{self.device.ip_address}]{Colors.END} Connecting again to the device")

        try:
            # Apply configuration on the device, sending a list of commands
            print(f"{Colors.OK_GREEN}[{self.device.ip_address}]{Colors.END} Applying configuration")
            self.output = self.device.connection.send_config_set(data.split('\n'))
            self.device.connection.save_config()
            self.status = "Done"

            if 'Invalid input detected' in self.output:
                print(f"{Colors.NOK_RED}[{self.device.ip_address}]{Colors.END} Command not found: {data}")
                self.status = 'Command not found'

        except Exception as exception:
            if 'Pattern not detected' in str(exception):
                print(f"{Colors.NOK_RED}[{self.device.ip_address}]{Colors.END} Pattern not detected on command: {data}")
                self.status = f"Error running command: {data}"
                return
            raise exception

        return self.output

class GetConfigs(Configs):
    '''
    Class used to get device configurations, parsing the output using textfsm whenever possible 
    '''

    def __init__(self, device, info: str) -> None:
        '''
        Constructor used to create a new object, passing to the super class the device object,
        used to interact with the devices
        '''
        super().__init__(device, info)

    @write_to_file
    def get_config(self, command: str) -> str:
        '''
        Get configurations from the device, running a "show" command and parsing the output
        whenever possible
        '''

        # Connection to the device couln't be made
        if self.device.connection == None:
            self.status = self.device.status
            raise Exception(f"[{self.device.ip_address}] {self.device.status}")
        # Reconnect to the device, since connection was closed
        elif not self.device.connection.is_alive():
            self.device.connect()
            print(f"{Colors.OK_YELLOW}[{self.device.ip_address}]{Colors.END} Connecting again to the device")

        try:
            print(f"{Colors.OK_GREEN}[{self.device.ip_address}]{Colors.END} Getting configuration: {command}")
            # For commands with bigger output, increase the read_timeout
            read_timeout = 600 if self.info == 'Configuration' else 100
            self.output = self.device.connection.send_command(command, read_timeout=read_timeout)
            self.status = "Done"

            if 'Invalid input detected' in self.output:
                print(f"{Colors.NOK_RED}[{self.device.ip_address}]{Colors.END} Command not found: {command}")
                self.status = 'Command not found'

        except Exception as exception:
            if 'Pattern not detected' in str(exception):
                print(f"{Colors.NOK_RED}[{self.device.ip_address}]{Colors.END} Pattern not detected on command: {command}")
                self.status = f"Error running command: {command}"
                return
            raise exception

        return self.output
    
    def parse_output(self, **kwargs) -> list|None:
        '''
        Use TextFSM to parse the output of the command. The get_structured_data receives the raw
        output, device platform and command issued.
        '''
        try:
            print(f"{Colors.OK_GREEN}[{self.device.ip_address}]{Colors.END} Parsing output: {kwargs['command']}")
            self.output_parsed = get_structured_data(**kwargs)
            # Delete output_parsed variable since output couldn't be converted
            if isinstance(self.output_parsed, str):
                print(f"{Colors.NOK_RED}[{self.device.ip_address}]{Colors.END} Couldn't parse the output of the command: {kwargs['command']}")
                del self.output_parsed
                return None

            return self.output_parsed

        except Exception as exception:
            print(f"{Colors.NOK_RED}[{self.device.ip_address}]{Colors.END} Couldn't parse the output of the command: {kwargs['command']}")
    
    def get_mac_vendor(self, mac: str) -> str:
        '''
        Function used to get the vendor name/designation from a list of mac addresses. It uses the
        package OuiLookup to get the data
        '''
        return list(OuiLookup().query(mac)[0].values())[0]