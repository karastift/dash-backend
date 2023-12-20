import os
import sys
import time
import json
import uuid
import logging
import subprocess
from threading import Thread, Event

import yaml
from flask_cors import CORS
from flask_socketio import SocketIO
from flask import Flask, request

from bluetooth import Bluetooth
from player import PlayerNotFoundException


flask_secret_key = os.environ.get('FLASK_SECRET_KEY', str(uuid.uuid4()))
dashboard_update_time = os.environ.get('DASHBOARD_UPDATE_TIME', '0.2')

# Configure logging with a custom format
log_formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%d/%b/%Y %H:%M:%S')
log_handler = logging.StreamHandler()
log_handler.setFormatter(log_formatter)

# use 'werkzeug' logger for my logs too
logger = logging.getLogger('werkzeug')
logger.addHandler(log_handler)
logger.setLevel(logging.DEBUG)

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = flask_secret_key
socketio = SocketIO(app, cors_allowed_origins="*")

# create bluetooth instance to use bluetoothctl features
bluetooth = Bluetooth(logger=logger)

# Event to signal the dashboard update thread to stop
stop_dashboard_updates_event = Event()

def shutdown_server():
    """
    Calls clean up function on instances creates (Player),
    schedules shutdown of machine,
    stops websocket server
    and exits program.
    """

    # Set the event to signal the dashboard update thread to stop
    logger.info('Sending stop signal to threads.')
    stop_dashboard_updates_event.set()

    # tell player to clean up
    logger.info('Cleaning up instances.')
    bluetooth.clean_up()

    # schedule shutdown on machine
    logger.info('Scheduling a shutdown.')
    subprocess.run(['shutdown', '-h', 'now'])

    # stop websocket server
    logger.info('Stopping websocket server.')
    socketio.stop()

    # exit program
    logger.info('Exiting program.')
    sys.exit()

# def update_and_send_player_data():
#     while True:
#         p.update()
#         socketio.emit('player_update', p.json_status())
#         time.sleep(5) # update every 5 seconds to save resources and i cant get the current playing anyways

def send_dashboard_data():
    """
    Creates an endless loop that sends updates to the dashboard per websocket (every 100ms).
    The data sent, involves vehicle specific data like kmh and rpm.
    """

    logger.info('Starting to send vehicle updates.')

    kmh = 0
    rpm = 0

    wait_time = float(dashboard_update_time)

    while not stop_dashboard_updates_event.is_set():
        kmh %= 200
        kmh += 5

        rpm %= 6000
        rpm += 100

        data_string = json.dumps({
            'kmh': kmh,
            'rpm': rpm,
        })

        socketio.emit('dashboard_update', data_string)
        time.sleep(wait_time)

@app.route('/bluetooth/<string:action>', methods=['POST'])
def bluetooth_endpoint(action):
    """
    :param action: 'discoverable' | 'pairing'
    :return: dictionary { 'error': string }
    """

    if action == 'discoverable':
        status = request.form.get('status')
        bluetooth.discoverable(status == 'true')

        return '', 200

    elif action == 'pairable':
        status = request.form.get('status')
        bluetooth.pairable(status == 'true')

        return '', 200
    else:
        return '', 404

@app.route('/player/<string:action>', methods=['POST'])
def player_endpoint(action):
    """
    :param action: 'play_pause' | 'forward' | 'back'
    :return: dictionary { 'title': str, 'interpret': str, 'length': int, 'isPlaying': bool }
    """

    if not bluetooth.player:
        
        try:
            player_names = bluetooth.list_players()

            # use the first player found
            bluetooth.set_player(player_names[0])
        except IndexError:
            return { 'error': 'A bluetooth connected device with music playing is required to use player actions.' }, 400

    # call player method corresponding to action

    try:
        if action == 'play_pause':
            bluetooth.player.toggle_play()

        # elif action == 'skip_to':
        #     percentage = request.form.get('percentage')
        #     response['current'] = p.skip_to(float(percentage))

        elif action == 'volume_to':
            percentage = request.form.get('percentage')
            bluetooth.player.set_volume(float(percentage))

        elif action == 'forward':
            bluetooth.player.next()

        elif action == 'back':
            bluetooth.player.previous()

        else: return '', 404
 
        # every player method should update the player instance by itsself
        # -> get the data from player instance and respond with it
        response = {
            'title': bluetooth.player.song['title'],
            'interpret': bluetooth.player.song['interpret'],
            'length': bluetooth.player.song['length'],
            'isPlaying': bluetooth.player.isPlaying,
            'volume': bluetooth.player.volume,
            'error': None,
        }

        return response, 200

    except PlayerNotFoundException:
        logger.warning('The player \'%s\' does not exist anymore.', bluetooth.player.bluez_player_path)
        logger.info('Setting player on bluetooth instance to None')
        bluetooth.unset_player()

        return { 'error': 'A bluetooth connected device with music playing is required to use player actions.' }, 400


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """
    Endpoint to shutdown the server. Calls shutdown_server() and returns nothing.
    """

    logger.warning('Shutdown of server was requested.')

    shutdown_server()
    return '', 200


if __name__ == '__main__':
    # start thread to send updated data for dashboard (vehicle data)
    update_dashboard_thread = Thread(target=send_dashboard_data)
    update_dashboard_thread.daemon = True
    update_dashboard_thread.start()

    # start thread to send updated data for player
    # update_player_thread = Thread(target=update_and_send_player_data)
    # update_player_thread.daemon = True
    # update_player_thread.start()

    socketio.run(app, '0.0.0.0', port=3333, debug=True, allow_unsafe_werkzeug=True)
