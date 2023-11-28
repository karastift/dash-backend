import json
import subprocess
from time import sleep


class Player():

    def __init__(self) -> None:

        self.bluez_player_name = self.get_bluez_player_name()

        self.song = {
            "title": "",
            "interpret": "",
            "length": 0, # in seconds
        }

        # how long the song has been played in seconds (not implemented because i cant get that info from bluetoothctl i think)
        # self.current = 0
        self.isPlaying = False

    def get_bluez_player_name(self) -> str:
        try:
            process = subprocess.Popen(['bluetoothctl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except:
            print('Error while opening bluetoothctl')

            return ''

        process.stdin.write('menu player\n')
        process.stdin.write('list\n')
        process.stdin.write('exit\n')

        out, err = process.communicate()

        player_name = ''

        for line in out.split('\n'):
            if line.startswith('Player'):
                try:
                    player_name = line.split(' ')[1]
                except:
                    print('bluez player has not been found')
                    return ''

        return player_name
    
    def bluez_player_commands(self, commands) -> str:
        if self.bluez_player_name == '':
            print('Could not execute command because bluez_player_name has not been set')
            return
        
        process = subprocess.Popen(['bluetoothctl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        process.stdin.write('menu player\n')
        process.stdin.write(f'select {self.bluez_player_name}\n')

        for command in commands:
            process.stdin.write(command + '\n')

        process.stdin.write('exit\n')
        
        out, err = process.communicate()

        return out

    def toggle_play(self) -> bool:
        self.isPlaying = not self.isPlaying

        if self.isPlaying:
            self.bluez_player_commands(['play'])
        else:
            self.bluez_player_commands(['pause'])
        
        # wait for player to update
        self.wait_and_update(0.2)
        
        return self.isPlaying
    
    def back(self):
        self.bluez_player_commands(['previous'])

        # wait for player to update
        self.wait_and_update(0.2)

        return self.song

    def forward(self):
        self.bluez_player_commands(['next'])

        # wait for player to update
        self.wait_and_update(0.2)

        return self.song

    # def skip_to(self, percentage: float) -> float:
    #     self.current = self.song['length'] * percentage / 100
    #     print("Skipped to (not implemented):", self.current, "seconds")

    #     return self.current
    
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
            print('error on updating')
    
    # there is nothing to clean up at the moment
    def clean_up(self):
        pass