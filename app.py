import time
import json
import logging
import subprocess
from threading import Thread

from flask_socketio import SocketIO
from flask import Flask, render_template, request

from player import Player

# used by threads that send dashboard updates per websocket
running = True

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vhneuezflszfnlfuf834hfu48fjiedhf93whiu2i2jdfjsd93ikerjnk'
socketio = SocketIO(app)

logger = logging.getLogger('werkzeug')
logger.disabled = False

# p = Player()
p = None

# clean up and shutdown
def shutdown_server():
    global running
    running = False

    p.clean_up()
    subprocess.run('poweroff')
    exit()

# def update_and_send_player_data():
#     while True:
#         p.update()
#         socketio.emit('player_update', p.json_status())
#         time.sleep(5) # update every 5 seconds to save resources and i cant get the current playing anyways

def send_dashboard_data():
    
    kmh = 0
    rpm = 0

    while running:
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

# Returns all necessary info, but server uses only websocket info at the moment
@app.route('/player/<string:action>', methods=['POST'])
def player(action):
    
    response = {
        'titel': '',
        'interpret': '',
        'current': 0,
        'length': 0,
        'isPlaying': False,
    }

    if action == 'play_pause':
        response['isPlaying'] = p.toggle_play()

    # elif action == 'skip_to':
    #     percentage = request.form.get('percentage')
    #     response['current'] = p.skip_to(float(percentage))

    elif action == 'forward':
        new_song = p.forward()

        response['titel'] = new_song['titel']
        response['interpret'] = new_song['interpret']
        response['length'] = new_song['length']

    elif action == 'back':
        new_song = p.back()

        response['titel'] = new_song['titel']
        response['interpret'] = new_song['interpret']
        response['length'] = new_song['length']

    else: return '', 404

    return response, 200

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown()
    return '', 200


if __name__ == '__main__':
    # start thread to send updated data for dashboard
    update_dashboard_thread = Thread(target=send_dashboard_data)
    update_dashboard_thread.daemon = True
    update_dashboard_thread.start()

    # start thread to send updated data for player
    # update_player_thread = Thread(target=update_and_send_player_data)
    # update_player_thread.daemon = True
    # update_player_thread.start()

    socketio.run(app, debug=True)
