from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import time
import math
import json
import os


with open("config/gameserver.json") as config_file:
    config = json.load(config_file)

port = config.get("port", 5000)
host = config.get("host", "0.0.0.0")


blue = "\033[34m"
yellow = "\033[33m"
white = "\033[37m"
reset = "\033[0m"
red = "\033[31m"


print(f"""{blue}
  GGGG    AA    M   M  EEEEE   SSSSS  EEEEE  RRRR   V   V  EEEEE RRRR  
 G       A  A   MM MM  E      S       E      R   R  V   V  E     R  R 
G  GGG  AAAA   M M M  EEEE    SSS    EEEE   RRRR   V   V  EEEE   RRR  
G    G  A  A   M   M  E          S   E      R  R   V   V  E      R  R  
 GGGG   A  A   M   M  EEEEE   SSSS   EEEEE  R   R   VVV   EEEEE  R   R 
{reset}""")
time.sleep(1)
print(f"{red}Attempting to start Game Server on IP -> {host}:{port}{reset}")
time.sleep(1)
print(f"{red}Please wait while we start the Server...{reset}")
time.sleep(1)
secret_key_pre2 = os.urandom(25)
print(f"{yellow}Your Secret Key for this Game Session is: {secret_key_pre2}{reset}")
time.sleep(3)


app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key_pre2
socketio = SocketIO(app, cors_allowed_origins="*")

players = {}
bullets = {}
rooms = {}
MAX_PLAYERS_PER_ROOM = 8

class Player:
    def __init__(self, player_id, name):
        self.id = player_id
        self.name = name
        self.x = 400
        self.y = 300
        self.angle = 0
        self.health = 100
        self.score = 0
        self.alive = True
        self.last_shot = 0
        self.room = None

class Bullet:
    def __init__(self, x, y, angle, owner_id):
        self.id = str(uuid.uuid4())
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * 5
        self.vy = math.sin(angle) * 5
        self.owner_id = owner_id
        self.created_at = time.time()

@app.route('/')
def game():
    return render_template('game.html')

@socketio.on('connect')
def on_connect(auth):
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def on_disconnect():
    print(f'Client disconnected: {request.sid}')
    if request.sid in players:
        player = players[request.sid]
        if player.room:
            leave_room(player.room)
            emit('player_left', {'player_id': request.sid}, room=player.room)
        del players[request.sid]

@socketio.on('join_game')
def on_join_game(data):
    player_name = data.get('name', 'Anonymous')
    
    room_id = None
    for room, room_data in rooms.items():
        if len(room_data['players']) < MAX_PLAYERS_PER_ROOM:
            room_id = room
            break
    
    if not room_id:
        room_id = str(uuid.uuid4())
        rooms[room_id] = {'players': []}
    
    player = Player(request.sid, player_name)
    player.room = room_id
    players[request.sid] = player
    rooms[room_id]['players'].append(request.sid)
    
    join_room(room_id)
    
    emit('game_joined', {
        'player_id': request.sid,
        'room_id': room_id,
        'players': {pid: {
            'name': players[pid].name,
            'x': players[pid].x,
            'y': players[pid].y,
            'angle': players[pid].angle,
            'health': players[pid].health,
            'score': players[pid].score,
            'alive': players[pid].alive
        } for pid in rooms[room_id]['players'] if pid in players}
    })
    
    emit('player_joined', {
        'player_id': request.sid,
        'name': player_name,
        'x': player.x,
        'y': player.y,
        'angle': player.angle,
        'health': player.health,
        'score': player.score,
        'alive': player.alive
    }, room=room_id, include_self=False)

@socketio.on('player_move')
def on_player_move(data):
    if request.sid not in players:
        return
    
    player = players[request.sid]
    player.x = max(25, min(775, data['x']))
    player.y = max(25, min(575, data['y']))
    player.angle = data['angle']
    
    emit('player_moved', {
        'player_id': request.sid,
        'x': player.x,
        'y': player.y,
        'angle': player.angle
    }, room=player.room, include_self=False)

@socketio.on('player_shoot')
def on_player_shoot():
    if request.sid not in players:
        return
    
    player = players[request.sid]
    current_time = time.time()
    
    if current_time - player.last_shot < 0.33 or not player.alive:
        return
    
    player.last_shot = current_time
    
    bullet = Bullet(player.x, player.y, player.angle, request.sid)
    bullets[bullet.id] = bullet
    
    emit('bullet_fired', {
        'bullet_id': bullet.id,
        'x': bullet.x,
        'y': bullet.y,
        'vx': bullet.vx,
        'vy': bullet.vy,
        'owner_id': bullet.owner_id
    }, room=player.room)

def update_bullets():
    """Update bullet positions and check for collisions"""
    bullets_to_remove = []
    
    for bullet_id, bullet in bullets.items():
        bullet.x += bullet.vx
        bullet.y += bullet.vy
        
        if (bullet.x < 0 or bullet.x > 800 or 
            bullet.y < 0 or bullet.y > 600 or 
            time.time() - bullet.created_at > 3):
            bullets_to_remove.append(bullet_id)
            continue
        
        if bullet.owner_id in players:
            owner = players[bullet.owner_id]
            for player_id, player in players.items():
                if (player_id != bullet.owner_id and 
                    player.room == owner.room and 
                    player.alive):
                    
                    distance = math.sqrt((bullet.x - player.x)**2 + (bullet.y - player.y)**2)
                    if distance < 20: 
                        player.health -= 25
                        bullets_to_remove.append(bullet_id)
                        
                        if player.health <= 0:
                            player.alive = False
                            player.health = 0
                            owner.score += 1
                            
                            socketio.emit('player_killed', {
                                'victim_id': player_id,
                                'killer_id': bullet.owner_id,
                                'killer_score': owner.score
                            }, room=player.room)
                            
                            socketio.start_background_task(respawn_player, player_id)
                        else:
                            socketio.emit('player_hit', {
                                'player_id': player_id,
                                'health': player.health,
                                'shooter_id': bullet.owner_id
                            }, room=player.room)
                        break
    
    for bullet_id in bullets_to_remove:
        if bullet_id in bullets:
            del bullets[bullet_id]
            socketio.emit('bullet_removed', {'bullet_id': bullet_id})

def respawn_player(player_id):
    socketio.sleep(3)
    if player_id in players:
        player = players[player_id]
        player.health = 100
        player.alive = True
        player.x = 400
        player.y = 300
        
        socketio.emit('player_respawned', {
            'player_id': player_id,
            'x': player.x,
            'y': player.y,
            'health': player.health
        }, room=player.room)

def game_loop():
    while True:
        update_bullets()
        socketio.sleep(1/60)

if __name__ == '__main__':
    socketio.start_background_task(game_loop)
    socketio.run(app, host=host, port=port)