import logging
import subprocess
from typing import List

from player import Player
from device import Device

    
class Bluetooth():
    """
    A python wrapper for the `bluetoothctl` utility.
    It needs the `bluetoothctl` utility installed on the system, without it, it will not work at all.
    """

    player: Player = None

    def __init__(self, bluetoothctl_path: str = 'bluetoothctl', logger: logging.Logger = None) -> None:

        # if logger is set, use it
        # if logger is not set a null_logger is created that wont log anything
        if logger:
            self.logger = logger
        else:
            # create a logger
            self.logger = logging.getLogger('null_logger')

            # create a NullHandler and add it to the logger
            null_handler = logging.NullHandler()
            self.logger.addHandler(null_handler)

            # set the logger level to NOTSET to capture all messages
            self.logger.setLevel(logging.NOTSET)
        
        self.bluetoothctl_path = bluetoothctl_path
        """Defines the path/name of the `bluetoothctl` program. You should change that to match the name/path of the tool on your system."""

        # check defined bluetoothctl path by trying to open a process
        # this will raise BluetoothctlNotFoundException if path is wrong
        self.commands([])

    def commands(self, commands: List[str], exit_after_commands = True) -> str:
        """
        Executes the list of commands against the `bluetootctl` program. Returns the all the output as string.

        Also sends 'exit' command after sending `commands[]`, if not specified otherwhise with `exit_after_commands`
        """

        try:
            # this could raise an exception if bluetoothctl is not preset on system
            process = subprocess.Popen([self.bluetoothctl_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        # file not found error is raised by Popen, when there is no program at `BLUETOOTHCTL_MODULE_NAME`
        # raise more specific error: BluetoothctlNotFound with the filename (name of program)
        except FileNotFoundError as error:
            raise BluetoothctlNotFoundException(error.filename)

        for command in commands:
            self.logger.info('Sending command to bluetoothctl: \'%s\'', command)
            process.stdin.write(command + '\n')

        if exit_after_commands: process.stdin.write('exit\n')
        
        out, err = process.communicate()

        if err:
            raise err

        return out
    
    def command(self, command: str) -> str:
        """
        Executes a command against the `bluetootctl` program. Returns the all the output as string.

        Uses the commands() method.
        """
        return self.commands([command])

    def list_players(self) -> List[str]:
        """
        Returns a list of all the specific bluez player names.
        """

        out = self.commands(['menu player', 'list'])

        player_names = list()

        for line in out.split('\n'):
            if line.startswith('Player'):
                player_names.append(line.split(' ')[1])

        return player_names

    def player_exists(self, player_name: str) -> bool:

        player_names = self.list_players()

        return player_name in player_names
    
    def set_player(self, player_name: str) -> None:
        """
        Creates an instance of player which uses `player_name` and sets it to self.player.
        """
        self.player = Player(
            # player class uses the commands function of this class to execute bluetoothctl commands
            self.commands,
            player_name,
            logger=self.logger,
        )
    
    def unset_player(self) -> None:
        self.player = None

    def pairable(self, status: bool) -> None:

        command = 'pairable ' + ('on' if status else 'off')

        self.command(command)

    def discoverable(self, status: bool) -> None:

        command = 'discoverable ' + ('on' if status else 'off')

        self.command(command)
    
    def list_devices(self) -> List[Device]:
        """
        Returns a list of all devices known.
        """

        out = self.command('devices')

        devices = list()

        for line in out.split('\n'):
            if line.startswith('Device'):
                try:
                    splitted = line.split(' ')
                    devices.append(Device(
                        name=splitted[2],
                        mac_address=splitted[1],
                    ))
                except Exception as e:
                    self.logger.error('Error while listing devices: %s', e)

        return devices
    
    def remove_device(self, mac_address: str) -> None:

        if not self.device_exists(mac_address): return

        command = 'remove ' + mac_address

        self.command(command)
    
    def device_exists(self, mac_address: str) -> bool:
        devices = self.list_devices()

        for device in devices:
            if device.mac_address == mac_address: return True
        
        return False

    def clean_up(self):
        """
        Cleans up. Should be called before exiting program or deleting bluetooth instance.
        """
        pass


class BluetoothctlNotFoundException(Exception):
    """
    Is raised when the bluetooth utility `bluetoothctl` was not found.
    """

    def __init__(self, bluetoothctl_name) -> None:
        super().__init__(f'The bluetooth utility was not found: `{bluetoothctl_name}`')
