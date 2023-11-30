import json
import logging

    
class DummyPlayer():

    songs = [
        {
            "title": "Life is a Highway",
            "interpret": "Rascal Flatts",
            "length": 332, # in seconds
        },
        {
            "title": "Son of a preacher Man",
            "interpret": "Bonny und Clyde",
            "length": 232, # in seconds
        },
        {
            "title": "Danger Zone",
            "interpret": "Kenny Loggins",
            "length": 432, # in seconds
        },
        {
            "title": "Money For Nothing",
            "interpret": "Dire Straits",
            "length": 503, # in seconds
        },
        {
            "title": "Peace of My Heart",
            "interpret": "Janis Joplin",
            "length": 340, # in seconds
        },
    ]

    current_song_index = 0
    volume = 0.5

    def __init__(self, logger: logging.Logger = None) -> None:

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
        
        self.logger.info('Initializing player.')

        self.song = {
            "title": "",
            "interpret": "",
            "length": 0, # in seconds
        }

        # how long the song has been played in seconds (not implemented because i cant get that info from bluetoothctl i think)
        # self.current = 0

        self.isPlaying = False

    def toggle_play(self) -> bool:

        self.isPlaying = not self.isPlaying

        return self.isPlaying
    
    def previous(self):

        self.current_song_index -= 1

        if self.current_song_index == -1:
            self.current_song_index = 4
        
        self.song = self.songs[self.current_song_index]

        return self.song

    def next(self):

        self.current_song_index += 1

        if self.current_song_index == 4:
            self.current_song_index = 0

        self.song = self.songs[self.current_song_index]

        return self.song
    
    def set_volume(self, percentage: float) -> None:
        self.volume = percentage

    def json_status(self):
        return json.dumps({
            # 'current': self.current,
            'isPlaying': self.isPlaying,
            'song': self.song,
        })
    
    def clean_up(self):
        """
        Cleans up. Should be called before exiting program or deleting player instance
        """
        pass