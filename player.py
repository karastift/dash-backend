import json
import logging
import subprocess
from time import sleep
from typing import List


BLUETOOTHCTL_MODULE_NAME = 'bluetoothctl'
"""Defines the path/name of the `bluetoothctl` program. You should change that to match the name/path of the tool on your system."""

AMIXER_MODULE_NAME = 'amixer'
"""Defines the path/name of the `amixer` program. You should change that to match the name/path of the tool on your system."""

    
class Player():
    """
    A python wrapper for the bluez player. It provides basic functionality to control the bluez player.
    It uses the `bluetoothctl` utility, without it, it will not work at all.
    """

    def __init__(self, player_name: str = '', wait_before_update_time: float = 0.2, logger: logging.Logger = None) -> None:
        """
        If `player_name` is not set, it searches for the first player it finds and uses it.
        If it cannot find a player and it has not been set, an exception is raised

        :param player_name: The name of the bluez player you want to use.
        """

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
        
        logger.info('Initializing player.')

        if player_name == '':
            # search for player
            # raises an exception if no player has been found
            self.bluez_player_name = get_bluez_player_name()
            logger.info('Found player: \'%s\'', self.bluez_player_name)
        else:
            if is_bluez_player_present(player_name):
                self.bluez_player_name = player_name
                logger.info('Successfully checked player: \'%s\'', self.bluez_player_name)
            else:
                raise PlayerNotFoundException(player_name)
                
        self.song = {
            "title": "",
            "interpret": "",
            "length": 0, # in seconds
        }

        # how long the song has been played in seconds (not implemented because i cant get that info from bluetoothctl i think)
        # self.current = 0

        self.isPlaying = False
        self.volume = 0.5

        # if None is passed, use 0.2
        self.wait_before_update_time = wait_before_update_time or 0.2

    def bluez_player_commands(self, commands: List[str]) -> str:
        """
        Selects the player currently set in class and executes the list of commands. Returns the all the output as string.
        """

        process = subprocess.Popen([BLUETOOTHCTL_MODULE_NAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        process.stdin.write('menu player\n')
        process.stdin.write(f'select {self.bluez_player_name}\n')

        for command in commands:
            self.logger.info('Sending command to player: \'%s\'', command)
            process.stdin.write(command + '\n')

        process.stdin.write('exit\n')
        
        out, err = process.communicate()

        if err:
            raise err

        return out

    def toggle_play(self) -> bool:
        """
        Toggles playing status und sends the play or pause to bluez player.
        Calls wait_and_update() afterwards.
        """

        self.isPlaying = not self.isPlaying

        if self.isPlaying:
            self.bluez_player_commands(['play'])
        else:
            self.bluez_player_commands(['pause'])
        
        # wait for player to update
        self.wait_and_update(self.wait_before_update_time)
        
        return self.isPlaying
    
    def previous(self):
        """
        Sends `previous` command to bluez player.
        Calls wait_and_update() afterwards.
        """

        self.bluez_player_commands(['previous'])

        # wait for player to update
        self.wait_and_update(self.wait_before_update_time)

        return self.song

    def next(self):
        """
        Sends `next` command to bluez player.
        Calls wait_and_update() afterwards.
        """

        self.bluez_player_commands(['next'])

        # wait for player to update
        self.wait_and_update(self.wait_before_update_time)

        return self.song

    # def skip_to(self, percentage: float) -> float:
    #     self.current = self.song['length'] * percentage / 100
    #     print("Skipped to (not implemented):", self.current, "seconds")

    #     return self.current

    def set_volume(self, percentage: float) -> None:
        self.volume = percentage

        percentage_string = str(percentage * 100) + '%'

        subprocess.run([AMIXER_MODULE_NAME, 'sset', 'Master', percentage_string])

    def json_status(self):
        return json.dumps({
            # 'current': self.current,
            'isPlaying': self.isPlaying,
            'song': self.song,
        })
    
    # used by methods which control the player and need an update of status
    # i cant just call update() because the player needs a bit time to get the new song information after changing track
    def wait_and_update(self, seconds):

        sleep(seconds)
        self.update()
    
    def update(self):

        self.logger.info('Updating player.')

        out = self.bluez_player_commands(['show'])

        try:
            for line in out.split('\n'):
                line = line.lstrip()

                if line.startswith('Status'):
                    self.isPlaying = 'playing' == line.split(': ')[1]
                elif line.startswith('Title'):
                    self.song['title'] = line.split(': ')[1]
                elif line.startswith('Artist'):
                    self.song['interpret'] = line.split(': ')[1]
                elif line.startswith('Duration'):
                    self.song['length'] = int(line.split(' ')[2][1:-1]) / 1000
                else: pass
        except:
            self.logger.error('Error on updating player.', exc_info=1)
    
    def clean_up(self):
        """
        Cleans up. Should be called before exiting program or deleting player instance
        """
        pass


def get_bluez_player_name() -> str:

    player_names = list_bluez_player_names()

    try:
        return player_names[0]
    except IndexError:
        raise NoPlayerFoundException()

def is_bluez_player_present(player_name: str) -> bool:

    player_names = list_bluez_player_names()

    return player_name in player_names

def list_bluez_player_names() -> List[str]:
    """
    Returns a list of all the specific bluez player names.
    """
    
    try:
        # this could raise an exception if bluetoothctl is not preset on system
        process = subprocess.Popen([BLUETOOTHCTL_MODULE_NAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    # file not found error is raised by Popen, when there is no program at `BLUETOOTHCTL_MODULE_NAME`
    # raise more specific error: BluetoothctlNotFound with the filename (name of program)
    except FileNotFoundError as error:
        raise BluetoothctlNotFoundException(error.filename)

    process.stdin.write('menu player\n')
    process.stdin.write('list\n')
    process.stdin.write('exit\n')

    out, err = process.communicate()

    if err:
        raise err

    player_names = list()

    for line in out.split('\n'):
        if line.startswith('Player'):
            player_names.append(line.split(' ')[1])

    return player_names

def bluetoothctl_commands(commands: List[str]) -> str:
    """
    Executes the list of commands against the `bluetootctl` program. Returns the all the output as string.
    """

    process = subprocess.Popen([BLUETOOTHCTL_MODULE_NAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    for command in commands:
        logging.getLogger().info('Sending command to bluetoothctl: \'%s\'', command)
        process.stdin.write(command + '\n')

    process.stdin.write('exit\n')
    
    out, err = process.communicate()

    if err:
        raise err

    return out

def set_pairing(status: bool) -> None:

    command = 'pairing ' + 'on' if status else 'off'

    bluetoothctl_commands([command])

def set_discoverable(self, status: bool) -> None:

    command = 'discoverable ' + 'on' if status else 'off'

    bluetoothctl_commands([command])
    

class BluetoothctlNotFoundException(Exception):
    """
    Is raised when the bluetooth utility `bluetoothctl` was not found.
    """

    def __init__(self, bluetoothctl_name) -> None:
        super().__init__(f'The bluetooth utility was not found: `{bluetoothctl_name}`')

class NoPlayerFoundException(Exception):
    """
    Is raised when no player_name was given at initialization of player and there is no player present.
    """

    def __init__(self, message='No player was found and no player_name was given.') -> None:
        super().__init__(message)

class PlayerNotFoundException(Exception):
    """
    Is raised when a player_name was given but the player is not listed by bluez.
    """

    def __init__(self, player_name: str) -> None:
        super().__init__(f'The given player `{player_name}` was not found.')