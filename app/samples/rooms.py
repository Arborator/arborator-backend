import time
from typing import Dict, Set

from flask_socketio import join_room, leave_room, send, SocketIO

users_in_app_tracking: Dict[str, float] = {}
users_in_rooms_tracking: Dict[str, Set[str]] = {}

def add_or_update_user_in_app_tracking(user):
    if user:
        users_in_app_tracking[user] = time.time()

def remove_user_in_app_tracking(user):
    if user in users_in_app_tracking:
        del users_in_app_tracking[user]

def who_is_connected_now():
    time_now = time.time()
    connected_users = []
    recent_disconnected_users = []
    for user, last_check_time in users_in_app_tracking.items():
        if time_now - last_check_time < 3 * 60:  # 3mn
            connected_users.append(user)
        else:
            if user:
                recent_disconnected_users.append(user)
    for recent_disconnected_user in recent_disconnected_users:
        del users_in_app_tracking[recent_disconnected_user]
    return connected_users, recent_disconnected_users

def add_user_in_room_tracking(username, room):
    if users_in_rooms_tracking.get(room):
        users_in_rooms_tracking[room].add(username)
    else:
        users_in_rooms_tracking[room] = set([username])

def remove_user_in_room_tracking(username, room):
    if users_in_rooms_tracking.get(room):
        users_in_rooms_tracking[room].remove(username)



def add_rooms_to_socket(socketio: SocketIO):
    print("Adding rooms logic to socket")
    @socketio.on('message')
    def handle_message(data):
        print('received message: ', data)

    @socketio.on('join_app')
    def handle_join_app(data):
        if data["username"] not in users_in_app_tracking:
            socketio.emit('connection_event' ,f'{data["username"]} just logged in')

        add_or_update_user_in_app_tracking(data["username"])
        print('join_app', data)

    @socketio.on('still_connected')
    def handle_still_connected(data):
        if not data["username"]:
            return
        print("Still connected", data["username"])
        add_or_update_user_in_app_tracking(data["username"])
        connected_users, recent_disconnected_users = who_is_connected_now()
        if len(recent_disconnected_users) >= 1:
            socketio.emit('connection_event' ,f'{", ".join(recent_disconnected_users)} just logged out')

    @socketio.on('leave_app')
    def handle_leave_app(data):
        remove_user_in_app_tracking(data["username"])
        print('leave_app', data)


    @socketio.on('join_project')
    def on_join_project(data):
        username = data['username']
        projectname = data['projectName']
        if not username:
            return
        join_room(projectname)
        add_user_in_room_tracking(username, projectname)
        send(username + ' has entered the room.', to=projectname)


    @socketio.on('leave_project')
    def on_leave_project(data):
        username = data['username']
        projectname = data['projectName']
        if not username:
            return
        leave_room(projectname)
        remove_user_in_room_tracking(username, projectname)
        send(username + ' has leaved the room.', to=projectname)

