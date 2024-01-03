import os
import sys
import time
import json
import uuid
import logging
import subprocess
from threading import Thread, Event

import obd
from flask_cors import CORS
from flask_socketio import SocketIO
from flask import Flask, request

from bluetooth import Bluetooth
from player import PlayerNotFoundException

flask_secret_key = os.environ.get('FLASK_SECRET_KEY', str(uuid.uuid4()))
dashboard_update_time = os.environ.get('DASHBOARD_UPDATE_TIME', '0.2')
obd_adapter_serial_name = os.environ.get('OBD_ADAPTER_SERIAL_NAME', 'serial')

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

# create connection to obd adapter
obd_conn: obd.Async = None

# Event to signal the dashboard update thread to stop
stop_obd_connection_loop = Event()

# Event to signal the player update thread to stop
stop_player_updates_event = Event()

def speed_update(speed):

    data = str(speed.value.magnitude) if not speed.is_null() else '0'

    socketio.emit('speed', data)

def rpm_update(rpm):

    data = str(rpm.value.magnitude) if not rpm.is_null() else '0'

    socketio.emit('rpm', data)

def init_obd():
    """
    Initializes a new obd connection and sets up watchers to send data per websocket.    
    """

    global obd_conn

    ports = obd.scan_serial()

    adapter_port = ''

    # my current adapter has 'serial' in the name so I use that to select it
    for port in ports:
        if obd_adapter_serial_name in port:
            logger.info('An obd adapter was found: %s', port)
            adapter_port = port
    
    if adapter_port == '':
        logger.error('No obd adapter was found')

    logger.info('Trying to initialize connection: \'%s\'', adapter_port)

    obd_conn = obd.Async(adapter_port if adapter_port else None)

    # dont start watchers, when no connection to car was made
    if obd_conn.status() != obd.OBDStatus.CAR_CONNECTED:
        logger.warning('Car is not connected on new connection: \'%s\'', adapter_port)
        return

    obd_conn.watch(obd.commands.RPM, callback=rpm_update)
    obd_conn.watch(obd.commands.SPEED, callback=speed_update)

    obd_conn.start()

def shutdown_server():
    """
    Calls clean up function on instances creates (Player),
    schedules shutdown of machine,
    stops websocket server
    and exits program.
    """

    # Set the event to signal the dashboard/player update thread to stop
    logger.info('Sending stop signal to threads.')
    stop_obd_connection_loop.set()
    stop_player_updates_event.set()

    # stop obd update loop
    obd_conn.stop()
    obd_conn.unwatch_all()

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

def update_and_send_player_data():
    """
    Creates an endless loop that sends updates to the dashboard per websocket.
    The data sent, involves player specific data like the song currently playing.
    """

    sleep_time = 5

    logger.info('Starting to send player updates.')

    while not stop_player_updates_event.is_set():

        logger.info('Trying to send player update')

        if not bluetooth.player:
            
            try:
                player_names = bluetooth.list_players()

                # use the first player found
                bluetooth.set_player(player_names[0])

                logger.info('A new player \'%s\' was found and set', bluetooth.player.bluez_player_path)

            except IndexError:

                logger.info('No player was found, sending player update with no data except for devices')

                devices = bluetooth.list_devices()

                socketio.emit('player_update', json.dumps({
                'title': '',
                'interpret': '',
                'length': 0,
                'isPlaying': False,
                'volume': 0,
                'devices': [device.__dict__ for device in devices],
                'error': 'A bluetooth connected device with music playing is required to use player actions.',
            }))

                time.sleep(sleep_time)
                continue
        
        try:

            bluetooth.player.update()
            devices = bluetooth.list_devices()

            data_string = json.dumps({
                'title': bluetooth.player.song['title'],
                'interpret': bluetooth.player.song['interpret'],
                'length': bluetooth.player.song['length'],
                'isPlaying': bluetooth.player.isPlaying,
                'volume': bluetooth.player.volume,
                'devices': [device.__dict__ for device in devices],
                'error': None,
            })

            logger.info('Sending player update:\n%s', data_string)

            socketio.emit('player_update', data_string)
        except PlayerNotFoundException:
            logger.warning('The player \'%s\' does not exist anymore.', bluetooth.player.bluez_player_path)
            logger.info('Setting player on bluetooth instance to None')
            bluetooth.unset_player()

            logger.info('Sending empty player update')

            socketio.emit('player_update', json.dumps({
            'title': '',
            'interpret': '',
            'length': 0,
            'isPlaying': False,
            'volume': 0,
            'error': 'A bluetooth connected device with music playing is required to use player actions.',
        }))

        time.sleep(sleep_time)

def obd_connection_loop():
    """
    First it calls init_obd(). After that it creates an endless loop that tries to initiate a connection over obd to the car.
    This also sends the current obd status as websocket update.
    """

    init_obd()

    while not stop_obd_connection_loop.is_set():
        time.sleep(5)

        if obd_conn.status() == obd.OBDStatus.CAR_CONNECTED:
            socketio.emit('obd_status', json.dumps({ 'message': 'Car connected' }))

            logger.info('Connected to car')
            continue

        # close connection, because a new one will be established
        obd_conn.close()
        init_obd()

        if obd_conn.status() == obd.OBDStatus.NOT_CONNECTED:

            socketio.emit('obd_status', json.dumps({ 'message': 'Not connected to the obd adapter' }))

            logger.error('No connection to obd adapter')


        elif obd_conn.status() == obd.OBDStatus.ELM_CONNECTED:
            socketio.emit('obd_status', json.dumps({ 'message': 'Connected to adapter, but no car was detected' }))

            logger.error('Connected to adapter \'%s\', but no car was detected', obd_conn.port_name())

        elif obd_conn.status() == obd.OBDStatus.OBD_CONNECTED:
            socketio.emit('obd_status', json.dumps({ 'message': 'Connected to car, ignition off' }))

            logger.info('Connected to car (through \'%s\'), ignition off', obd_conn.port_name())

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

    elif action == 'devices':
        
        devices = bluetooth.list_devices()

        return json.dumps([device.__dict__ for device in devices]), 200

    elif action == 'remove_device':
        mac_address = request.form.get('mac_address')

        devices = bluetooth.remove_device(mac_address)

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
    # start thread to create obd connection
    update_dashboard_thread = Thread(target=obd_connection_loop)
    update_dashboard_thread.daemon = True
    update_dashboard_thread.start()

    # start thread to send updated data for player
    update_player_thread = Thread(target=update_and_send_player_data)
    update_player_thread.daemon = True
    update_player_thread.start()

    socketio.run(app, '0.0.0.0', port=3333, debug=True, allow_unsafe_werkzeug=True)
