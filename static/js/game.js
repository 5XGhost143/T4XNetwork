const socket = io();
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

let gameState = {
    players: {},
    bullets: {},
    myPlayerId: null,
    myPlayer: null,
    keys: {},
    mouseX: 0,
    mouseY: 0
};

socket.on('game_joined', (data) => {
    gameState.myPlayerId = data.player_id;
    gameState.players = data.players;
    gameState.myPlayer = gameState.players[gameState.myPlayerId];
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('gameScreen').style.display = 'block';
    updateUI();
    startGameLoop();
});

socket.on('player_joined', (data) => {
    gameState.players[data.player_id] = data;
    updatePlayersList();
});

socket.on('player_left', (data) => {
    delete gameState.players[data.player_id];
    updatePlayersList();
});

socket.on('player_moved', (data) => {
    if (gameState.players[data.player_id]) {
        Object.assign(gameState.players[data.player_id], { x: data.x, y: data.y, angle: data.angle });
    }
});

socket.on('bullet_fired', (data) => {
    gameState.bullets[data.bullet_id] = data;
});

socket.on('bullet_removed', (data) => {
    delete gameState.bullets[data.bullet_id];
});

socket.on('player_hit', (data) => {
    if (gameState.players[data.player_id]) {
        gameState.players[data.player_id].health = data.health;
        if (data.player_id === gameState.myPlayerId) updateUI();
    }
});

socket.on('player_killed', (data) => {
    if (gameState.players[data.victim_id]) {
        gameState.players[data.victim_id].alive = false;
        gameState.players[data.victim_id].health = 0;
    }
    if (gameState.players[data.killer_id]) {
        gameState.players[data.killer_id].score = data.killer_score;
    }
    if (data.victim_id === gameState.myPlayerId) showDeathScreen();
    updateUI();
    updatePlayersList();
});

socket.on('player_respawned', (data) => {
    if (gameState.players[data.player_id]) {
        Object.assign(gameState.players[data.player_id], { alive: true, health: data.health, x: data.x, y: data.y });
        if (data.player_id === gameState.myPlayerId) {
            hideDeathScreen();
            updateUI();
        }
    }
});

function joinGame() {
    const name = document.getElementById('playerName').value.trim() || 'Anonymous';
    socket.emit('join_game', { name });
}

function startGameLoop() {
    setupControls();
    gameLoop();
}

function gameLoop() {
    update();
    render();
    requestAnimationFrame(gameLoop);
}

function update() {
    if (!gameState.myPlayer || !gameState.myPlayer.alive) return;
    let dx = 0, dy = 0, speed = 3;
    if (gameState.keys['w'] || gameState.keys['W']) dy -= speed;
    if (gameState.keys['s'] || gameState.keys['S']) dy += speed;
    if (gameState.keys['a'] || gameState.keys['A']) dx -= speed;
    if (gameState.keys['d'] || gameState.keys['D']) dx += speed;

    if (dx || dy) {
        gameState.myPlayer.x = Math.max(25, Math.min(775, gameState.myPlayer.x + dx));
        gameState.myPlayer.y = Math.max(25, Math.min(575, gameState.myPlayer.y + dy));
        gameState.myPlayer.angle = Math.atan2(gameState.mouseY - gameState.myPlayer.y, gameState.mouseX - gameState.myPlayer.x);
        socket.emit('player_move', { x: gameState.myPlayer.x, y: gameState.myPlayer.y, angle: gameState.myPlayer.angle });
    }

    for (let bulletId in gameState.bullets) {
        let bullet = gameState.bullets[bulletId];
        bullet.x += bullet.vx;
        bullet.y += bullet.vy;
    }
}

function render() {
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#1a1a2e');
    gradient.addColorStop(0.5, '#16213e');
    gradient.addColorStop(1, '#0f0f23');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = 'rgba(0, 212, 255, 0.15)';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 50) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 50) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    for (let playerId in gameState.players) drawPlayer(gameState.players[playerId], playerId === gameState.myPlayerId);
    for (let bulletId in gameState.bullets) drawBullet(gameState.bullets[bulletId]);
}

function drawPlayer(player, isMe) {
    if (!player.alive) return;
    ctx.save(); ctx.translate(player.x, player.y);
    ctx.shadowColor = isMe ? '#00d4ff' : '#ff006e'; ctx.shadowBlur = isMe ? 20 : 15;
    ctx.rotate(player.angle);

    const bodyGradient = ctx.createRadialGradient(0, 0, 5, 0, 0, 15);
    if (isMe) { bodyGradient.addColorStop(0, '#00d4ff'); bodyGradient.addColorStop(1, '#0099cc'); }
    else { bodyGradient.addColorStop(0, '#ff006e'); bodyGradient.addColorStop(1, '#cc0055'); }
    ctx.fillStyle = bodyGradient; ctx.fillRect(-15, -10, 30, 20);

    ctx.fillStyle = isMe ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.6)'; ctx.fillRect(-8, -5, 16, 10);
    ctx.fillStyle = '#ffffff'; ctx.shadowBlur = 10; ctx.fillRect(15, -2, 20, 4);
    ctx.fillStyle = isMe ? '#00d4ff' : '#ff006e'; ctx.fillRect(33, -1, 4, 2);
    ctx.restore();

    if (player.health < 100) {
        ctx.fillStyle = 'rgba(0,0,0,0.7)'; ctx.fillRect(player.x-20, player.y-30,40,8);
        ctx.strokeStyle = 'rgba(255,255,255,0.3)'; ctx.lineWidth=1; ctx.strokeRect(player.x-20, player.y-30,40,8);
        const healthGradient = ctx.createLinearGradient(player.x-20,0,player.x+20,0);
        if (player.health>66) healthGradient.addColorStop(0,'#00ff88'),healthGradient.addColorStop(1,'#00cc66');
        else if (player.health>33) healthGradient.addColorStop(0,'#ffaa00'),healthGradient.addColorStop(1,'#ff8800');
        else healthGradient.addColorStop(0,'#ff3b3b'),healthGradient.addColorStop(1,'#cc0000');
        ctx.fillStyle=healthGradient; ctx.fillRect(player.x-19,player.y-29,(player.health/100)*38,6);
    }
    ctx.save(); ctx.shadowColor=isMe?'#00d4ff':'#ff006e'; ctx.shadowBlur=10; ctx.fillStyle='white';
    ctx.font='bold 12px Orbitron, monospace'; ctx.textAlign='center'; ctx.fillText(player.name,player.x,player.y-35);
    ctx.restore();
}

function drawBullet(bullet) {
    ctx.fillStyle = '#f1c40f';
    ctx.beginPath(); ctx.arc(bullet.x, bullet.y, 3, 0, 2 * Math.PI); ctx.fill();
}

function setupControls() {
    document.addEventListener('keydown', e => gameState.keys[e.key] = true);
    document.addEventListener('keyup', e => gameState.keys[e.key] = false);
    canvas.addEventListener('mousemove', e => {
        const rect = canvas.getBoundingClientRect();
        gameState.mouseX = e.clientX - rect.left;
        gameState.mouseY = e.clientY - rect.top;
    });
    canvas.addEventListener('click', () => { if (gameState.myPlayer?.alive) socket.emit('player_shoot'); });
    canvas.addEventListener('contextmenu', e => e.preventDefault());
}

function updateUI() {
    if (gameState.myPlayer) {
        document.getElementById('health').textContent = `❤️ Health: ${gameState.myPlayer.health}`;
        document.getElementById('score').textContent = `🎯 Points: ${gameState.myPlayer.score}`;
    }
}

function updatePlayersList() {
    const playersDiv = document.getElementById('players'); playersDiv.innerHTML = '';
    Object.values(gameState.players).sort((a,b)=>b.score-a.score).forEach(player => {
        const playerDiv=document.createElement('div'); playerDiv.className='player-item';
        playerDiv.innerHTML=`<span>${player.name} ${player.alive?'🟢':'💀'}</span><span>🎯 ${player.score}</span>`;
        playersDiv.appendChild(playerDiv);
    });
}

function showDeathScreen() {
    document.getElementById('deadOverlay').style.display='block'; let countdown=3;
    const timer=setInterval(()=>{document.getElementById('respawnTimer').textContent=countdown; countdown--;
        if(countdown<0) clearInterval(timer);},1000);
}

function hideDeathScreen() {
    document.getElementById('deadOverlay').style.display='none';
}

document.getElementById('playerName').addEventListener('keypress', e => { if(e.key==='Enter') joinGame(); });
