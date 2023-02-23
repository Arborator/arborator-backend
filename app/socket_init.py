from flask_socketio import SocketIO
from app.samples.rooms import add_rooms_to_socket

socketio = SocketIO()

add_rooms_to_socket(socketio)