import json
import logging
import subprocess
from time import sleep
from typing import Callable, List


amixer_module_path = 'amixer'
"""Defines the path/name of the `amixer` program. You should change that to match the name/path of the tool on your system."""

    
class Player():
    """
    A python wrapper for the bluez player. It provides basic functionality to control the bluez player.
    It uses the `bluetoothctl` utility, without it, it will not work at all.
    """

    def __init__(self, bluetoothctl_commands: Callable[[List[str]], str], player_name: str, wait_before_update_time: float = 0.2, logger: logging.Logger = None) -> None:
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

        self.bluetoothctl_commands = bluetoothctl_commands
        """The function to be used when executing bluetoothctl_commands. It needs take in a list of commands to return the output as a string."""
        
        logger.info('Initializing player.')

        self.bluez_player_path = player_name
        """
        The path of the bluez player that should be used underneath.
        """

        if player_name == '' or not self.exists():
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
    
    def commands(self, commands: List[str]) -> str:
        """
        Selects the player currently set in class and executes the list of commands. Returns the all the output as string.

        Uses `bluetoothctl_commands` function which was passed on initialization.
        """

        # selects player before executing commands
        new_command_list = ['menu player', f'select {self.bluez_player_path}'].extend(commands)

        out = self.bluetoothctl_commands(new_command_list)

        return out

    def command(self, command: str) -> str:
        """
        Selects the player currently set in class and executes the command. Returns the all the output as string.

        Uses `self.commands()` function.
        """

        return self.commands([command])

    def toggle_play(self) -> bool:
        """
        Toggles playing status und sends the play or pause to bluez player.
        Calls wait_and_update() afterwards.
        """

        self.isPlaying = not self.isPlaying

        if self.isPlaying:
            self.command('play')
        else:
            self.command('pause')
        
        # wait for player to update
        self.wait_and_update(self.wait_before_update_time)
        
        return self.isPlaying
    
    def previous(self):
        """
        Sends `previous` command to bluez player.
        Calls wait_and_update() afterwards.
        """

        self.command('previous')


        # wait for player to update
        self.wait_and_update(self.wait_before_update_time)

        return self.song

    def next(self):
        """
        Sends `next` command to bluez player.
        Calls wait_and_update() afterwards.
        """

        self.command('next')

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

        subprocess.run([amixer_module_path, 'sset', 'Master', percentage_string])

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

        out = self.command('show')

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

    def exists(self) -> bool:
        """
        Returns True/False depending on if the player still exists.
        """
        return self.bluez_player_path in self.bluetoothctl_commands(['menu player', 'list']).split(' ')
    
    def clean_up(self):
        """
        Cleans up. Should be called before exiting program or deleting player instance
        """
        self.command('exit')


class PlayerNotFoundException(Exception):
    """
    Is raised when a player_name was given but the player is not listed by bluetoothctl.

    This can also happen if the player you used, does not exist anymore because the device disconnected for example.
    """

    def __init__(self, player_name: str) -> None:
        super().__init__(f'The given player `{player_name}` was not found.')