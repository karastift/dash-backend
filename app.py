import sys
import time
import json
import subprocess
from threading import Thread, Event

from flask_socketio import SocketIO
from flask import Flask, render_template, request

from player import Player

# Event to signal the dashboard update thread to stop
stop_dashboard_updates_event = Event()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vhneuezflszfnlfuf834hfu48fjiedhf93whiu2i2jdfjsd93ikerjnk'
socketio = SocketIO(app)

# create instance of player
player = Player()

def shutdown_server():
    """
    Calls clean up function on instances creates (Player),
    schedules shutdown of machine,
    stops websocket server
    and exits program.
    """


    # Set the event to signal the dashboard update thread to stop
    stop_dashboard_updates_event.set()

    # tell player to clean up
    player.clean_up()

    # schedule shutdown on machine
    subprocess.run('shutdown -h now')

    # stop websocket server
    socketio.stop()

    # if server runs with werkzeug, use the shutdown_func
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('Not running werkzeug')
    shutdown_func()

    # exit program
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
    
    kmh = 0
    rpm = 0

    while not stop_dashboard_updates_event.isSet():
        kmh %= 200
        kmh += 5

        rpm %= 6000
        rpm += 100

        data_string = json.dumps({
            'kmh': kmh,
            'rpm': rpm,
        })

        socketio.emit('dashboard_update', data_string)
        time.sleep(0.1)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/player/<string:action>', methods=['POST'])
def player_endpoint(action):
    """
    Calls corresponding method on player to action parameter and returns new song information (from player) as json.

    :param action: 'play_pause' | 'forward' | 'back'
    :return: dictionary { 'title': str, 'interpret': str, 'length': int, 'isPlaying': bool }
    """

    # call player method corresponding to action

    if action == 'play_pause':
        player.toggle_play()

    # elif action == 'skip_to':
    #     percentage = request.form.get('percentage')
    #     response['current'] = p.skip_to(float(percentage))

    elif action == 'forward':
        player.next()

    elif action == 'back':
        player.previous()

    else: return '', 404
    
    # every player method should update the player instance by itsself
    # -> get the data from player instance and respond with it
    response = {
        'title': player.song['title'],
        'interpret': player.song['interpret'],
        'length': player.song['length'],
        'isPlaying': player.isPlaying,
    }

    return response, 200

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """
    Endpoint to shutdown the server. Calls shutdown_server() and returns nothing.
    """

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

    socketio.run(app, 'localhost', debug=True)
