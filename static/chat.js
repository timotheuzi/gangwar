// Simple chat and PVP functionality for the alleyway

// Global variables
var socket = null;
var currentRoom = 'global'; // Global chat room
var locationRoom = 'city'; // Location-specific room for player list and PVP
var playerName = 'Player'; // Default name
var isConnected = false;

// Initialize SocketIO connection
function initSocketIO() {
    if (typeof io === 'undefined') {
        console.log('SocketIO not available');
        return;
    }

    // Get values from global window object set by template
    if (window.playerName) {
        playerName = window.playerName;
    }
    if (window.currentRoom) {
        currentRoom = window.currentRoom;
    }
    if (window.locationRoom) {
        locationRoom = window.locationRoom;
    }

    socket = io();

    socket.on('connect', function() {
        console.log('Connected to server');
        isConnected = true;
        updateConnectionStatus(true);

        socket.emit('join', {room: currentRoom, location_room: locationRoom, player_name: playerName});
        refreshPlayerList();
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        isConnected = false;
        updateConnectionStatus(false);
    });

    socket.on('connect_error', function(error) {
        console.log('Connection error:', error);
        isConnected = false;
        updateConnectionStatus(false);
    });

    socket.on('status', function(data) {
        console.log(data.msg);
        addChatMessage('System', data.msg, 'status');
        refreshPlayerList();
    });

    socket.on('chat_message', function(data) {
        // Include room info in chat message if it's from a different room
        var message = data.message;
        if (data.room && data.room !== currentRoom) {
            message = `[${data.room}] ${message}`;
        }
        var messageClass = data.message_class || null;
        addChatMessage(data.player, message, messageClass);
    });

    socket.on('player_list', function(data) {
        updatePVPPlayerList(data.players || []);
    });

    socket.on('pvp_response', function(data) {
        if (data.success) {
            showNotification(data.message, 'success');
        } else {
            showNotification(data.message, 'error');
        }
    });
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    var indicator = document.getElementById('connection-indicator');
    var text = document.getElementById('connection-text');
    if (indicator && text) {
        if (connected) {
            indicator.style.color = '#00ff00'; // Green
            text.textContent = 'Connected';
        } else {
            indicator.style.color = '#ff0000'; // Red
            text.textContent = 'Disconnected';
        }
    }
}

// Get game state from session (simplified)
function getGameState() {
    // This is a simplified version - in reality you'd need to get this from Flask session
    return null;
}

// Add chat message to chat area
function addChatMessage(player, message, messageClass) {
    var chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        var messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message';
        if (messageClass) {
            messageDiv.classList.add(messageClass);
        }

        // Ensure we use the actual player name, not fallback "Player"
        var displayName = player;
        if (player === 'Player' && window.playerName && window.playerName !== 'Player') {
            displayName = window.playerName;
        }

        messageDiv.innerHTML = '<strong>' + displayName + ':</strong> ' + message;
        chatMessages.appendChild(messageDiv);

        // Limit chat messages to prevent overflow
        var maxMessages = 50;
        while (chatMessages.children.length > maxMessages) {
            chatMessages.removeChild(chatMessages.firstChild);
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Update PVP player list
function updatePVPPlayerList(players) {
    var pvpListDiv = document.getElementById('pvp-player-list');
    if (!pvpListDiv) return;

    if (!players || players.length === 0) {
        pvpListDiv.innerHTML = '<p>No players online</p>';
        return;
    }

    var html = '<ul class="player-list">';
    players.forEach(function(player) {
        var playerStatus = player.in_fight ? ' (In Fight)' : '';
        var joinTime = new Date(player.joined_at * 1000).toLocaleTimeString();
        html += '<li class="player-item">';
        html += '<span class="player-name">' + player.name + '</span>';
        html += '<span class="player-info">Location: ' + player.room + playerStatus + '</span>';
        html += '<span class="player-join-time">Joined: ' + joinTime + '</span>';
        html += '</li>';
    });
    html += '</ul>';

    pvpListDiv.innerHTML = html;
}

// Send chat message
function sendChatMessage() {
    if (!socket || !isConnected) {
        showNotification('Not connected to server. Please wait...', 'error');
        return;
    }

    var input = document.getElementById('chat-input');
    if (!input) return;

    var message = input.value.trim();
    if (message && message.length <= 200) {
        socket.emit('chat_message', {
            room: currentRoom,
            player_name: playerName,
            message: message
        });
        input.value = '';
    }
}

// Refresh player list
function refreshPlayerList() {
    if (!socket || !isConnected) {
        showNotification('Not connected to server. Please wait...', 'error');
        return;
    }

    socket.emit('get_player_list', {room: locationRoom});
}

// Challenge player to PVP
function challengePlayer(playerId, playerName) {
    if (!socket || !isConnected) {
        showNotification('Not connected to server. Please wait...', 'error');
        return;
    }

    socket.emit('pvp_challenge', {
        room: locationRoom,
        target_id: playerId
    });
}

// Show notification
function showNotification(message, type) {
    // Create a simple notification
    var notification = document.createElement('div');
    notification.className = 'notification notification-' + type;
    notification.textContent = message;
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: ' + (type === 'success' ? '#4CAF50' : '#F44336') + '; color: white; padding: 10px; border-radius: 5px; z-index: 10000;';
    document.body.appendChild(notification);

    setTimeout(function() {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// Handle command buttons
function handleCommand(command) {
    var inputField = document.getElementById('chat-input');
    if (inputField) {
        inputField.value = command;
        sendChatMessage();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize SocketIO
    initSocketIO();

    // Set up chat input handler
    var sendButton = document.getElementById('send-chat');
    var inputField = document.getElementById('chat-input');

    if (sendButton) {
        sendButton.addEventListener('click', sendChatMessage);
    }

    if (inputField) {
        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
    }

    // Set up command buttons
    var commandButtons = document.querySelectorAll('.cmd-btn');
    commandButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            var command = this.getAttribute('data-command');
            if (command) {
                handleCommand(command);
            }
        });
    });

    // Set up refresh players button
    var refreshButton = document.getElementById('refresh-players');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshPlayerList);
    }
});

// Export functions for global access
window.sendChatMessage = sendChatMessage;
window.refreshPlayerList = refreshPlayerList;
window.challengePlayer = challengePlayer;
window.handleCommand = handleCommand;
