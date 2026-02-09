// Simple chat and PVP functionality for the Gang War game

// Global variables
var socket = null;
var currentRoom = 'global';
var locationRoom = 'city';
var playerName = 'Player';
var isConnected = false;
var currentPlayerId = null;
var reconnectAttempts = 0;
var maxReconnectAttempts = 5;

// Initialize SocketIO connection
function initSocketIO() {
    console.log('Initializing SocketIO connection...');
    
    // Wait for DOM to be ready and SocketIO library to be loaded
    function tryConnect() {
        if (typeof io !== 'undefined') {
            console.log('SocketIO library found, starting connection...');
            startSocketIO();
        } else {
            console.log('SocketIO library not yet loaded, waiting...');
            // Dynamically load SocketIO if not available
            if (!document.querySelector('script[src*="socket.io"]')) {
                console.log('Loading SocketIO from CDN...');
                var script = document.createElement('script');
                script.src = 'https://cdn.socket.io/4.0.0/socket.io.min.js';
                script.onload = function() {
                    console.log('SocketIO loaded from CDN');
                    setTimeout(startSocketIO, 100);
                };
                script.onerror = function() {
                    console.error('Failed to load SocketIO from CDN');
                    updateConnectionStatus(false, 'CDN load failed');
                };
                document.head.appendChild(script);
            }
            setTimeout(tryConnect, 500);
        }
    }
    
    setTimeout(tryConnect, 100);
}

function startSocketIO() {
    console.log('startSocketIO called');
    
    // Get values from global window object set by template
    if (window.playerName) {
        playerName = window.playerName;
        console.log('Player name from template:', playerName);
    }
    if (window.currentRoom) {
        currentRoom = window.currentRoom;
    }
    if (window.locationRoom) {
        locationRoom = window.locationRoom;
        console.log('Location room:', locationRoom);
    }

    // Clean up existing socket if any
    if (socket) {
        try {
            socket.disconnect();
        } catch (e) {
            console.log('Error disconnecting existing socket:', e);
        }
    }

    try {
        console.log('Creating new SocketIO connection to:', window.location.origin);
        
        socket = io({
            reconnection: true,
            reconnectionAttempts: maxReconnectAttempts,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 3000,
            transports: ['websocket', 'polling'],
            timeout: 10000,
            autoConnect: true
        });

        // Connection event handlers
        socket.on('connect', function() {
            console.log('SocketIO connected! Socket ID:', socket.id);
            isConnected = true;
            currentPlayerId = socket.id;
            reconnectAttempts = 0;
            updateConnectionStatus(true, 'Connected');
            
            // Join the chat rooms
            console.log('Joining rooms:', currentRoom, locationRoom);
            socket.emit('join', {
                room: currentRoom, 
                location_room: locationRoom, 
                player_name: playerName
            });
            
            // Refresh player list
            setTimeout(refreshPlayerList, 500);
        });

        socket.on('connect_error', function(error) {
            console.error('Connection error:', error);
            isConnected = false;
            reconnectAttempts++;
            var reason = 'Connection error';
            if (reconnectAttempts >= maxReconnectAttempts) {
                reason = 'Max reconnect attempts reached';
            }
            updateConnectionStatus(false, reason);
        });

        socket.on('connect_timeout', function() {
            console.log('Connection timeout');
            isConnected = false;
            updateConnectionStatus(false, 'Connection timeout');
        });

        socket.on('disconnect', function(reason) {
            console.log('Disconnected from server:', reason);
            isConnected = false;
            updateConnectionStatus(false, 'Disconnected: ' + reason);
        });

        socket.on('reconnect', function(attemptNumber) {
            console.log('Reconnected after', attemptNumber, 'attempts');
            isConnected = true;
            currentPlayerId = socket.id;
            reconnectAttempts = 0;
            updateConnectionStatus(true, 'Reconnected');
            
            // Re-join rooms
            socket.emit('join', {
                room: currentRoom, 
                location_room: locationRoom, 
                player_name: playerName
            });
        });

        socket.on('reconnect_attempt', function(attemptNumber) {
            console.log('Reconnection attempt', attemptNumber);
            updateConnectionStatus(false, 'Reconnecting...');
        });

        socket.on('reconnect_error', function(error) {
            console.error('Reconnection error:', error);
        });

        socket.on('reconnect_failed', function() {
            console.error('Reconnection failed');
            isConnected = false;
            updateConnectionStatus(false, 'Reconnection failed');
            showNotification('Unable to connect to chat server. Please refresh the page.', 'error');
        });

        // Game event handlers
        socket.on('status', function(data) {
            console.log('Status message:', data.msg);
            if (data.msg) {
                addChatMessage('System', data.msg, 'system');
            }
            refreshPlayerList();
        });

        socket.on('chat_message', function(data) {
            console.log('Chat message received:', data);
            addChatMessage(data.player, data.message, data.message_class || null);
        });

        socket.on('player_list', function(data) {
            console.log('Player list received:', data.players);
            updatePVPPlayerList(data.players || []);
        });

        socket.on('pvp_response', function(data) {
            if (data.success) {
                showNotification(data.message, 'success');
            } else {
                showNotification(data.message, 'error');
            }
        });

        // Trigger connection
        socket.connect();
        console.log('Socket connect() called');
        
    } catch (e) {
        console.error('Error creating SocketIO connection:', e);
        updateConnectionStatus(false, 'Error: ' + e.message);
    }
}

// Update connection status indicator
function updateConnectionStatus(connected, reason) {
    console.log('updateConnectionStatus called:', connected, reason);
    
    var indicator = document.getElementById('connection-indicator');
    var text = document.getElementById('connection-text');
    
    // Always try to update text element at minimum
    if (text) {
        if (connected) {
            if (indicator) {
                indicator.style.color = '#00ff00';
            }
            text.textContent = 'Connected';
            text.style.color = '#00ff00';
        } else {
            if (indicator) {
                indicator.style.color = '#ff0000';
            }
            text.textContent = reason || 'Disconnected';
            text.style.color = '#ff0000';
        }
    } else {
        console.warn('Connection status elements not found in DOM');
        // Show notification as fallback
        if (!connected) {
            showNotification('Chat disconnected: ' + (reason || 'Unknown reason'), 'error');
        }
    }
}

// Add chat message to chat area
function addChatMessage(player, message, messageClass) {
    var chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) {
        console.warn('Chat messages container not found');
        return;
    }
    
    var messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message';
    if (messageClass) {
        messageDiv.classList.add(messageClass);
    }
    
    // Sanitize message content
    var safePlayer = player ? player.replace(/</g, '<').replace(/>/g, '>') : 'Unknown';
    var safeMessage = message ? message.replace(/</g, '<').replace(/>/g, '>') : '';
    
    messageDiv.innerHTML = '<strong>' + safePlayer + ':</strong> ' + safeMessage;
    chatMessages.appendChild(messageDiv);

    // Limit chat messages to prevent overflow
    var maxMessages = 50;
    while (chatMessages.children.length > maxMessages) {
        chatMessages.removeChild(chatMessages.firstChild);
    }

    // Auto-scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Update PVP player list
function updatePVPPlayerList(players) {
    var pvpListDiv = document.getElementById('pvp-player-list');
    if (!pvpListDiv) {
        console.warn('PVP player list container not found');
        return;
    }

    if (!players || players.length === 0) {
        pvpListDiv.innerHTML = '<p>No players online</p>';
        return;
    }

    var html = '<h4>Online Players (' + players.length + ')</h4><ul>';
    players.forEach(function(player) {
        html += '<li>';
        var safeName = player.name ? player.name.replace(/</g, '<').replace(/>/g, '>') : 'Unknown';
        html += '<strong>' + safeName + '</strong>';
        if (player.location) {
            html += ' <small>(in ' + player.location + ')</small>';
        }
        if (player.id !== currentPlayerId) {
            var safeId = player.id ? player.id.replace(/'/g, "\\'") : '';
            var safeName = player.name ? player.name.replace(/'/g, "\\'") : '';
            html += ' <button class="btn btn-small" onclick="challengePlayer(\'' + safeId + '\', \'' + safeName + '\')">Challenge</button>';
        }
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
        console.log('Sending chat message:', message);
        socket.emit('chat_message', {
            room: currentRoom,
            player_name: playerName,
            message: message
        });
        input.value = '';
    } else if (message.length > 200) {
        showNotification('Message too long (max 200 characters)', 'error');
    }
}

// Refresh player list
function refreshPlayerList() {
    if (!socket || !isConnected) {
        showNotification('Not connected to server. Please wait...', 'error');
        return;
    }

    console.log('Requesting player list...');
    socket.emit('get_player_list', {room: locationRoom});
}

// Challenge player to PVP
function challengePlayer(playerId, playerName) {
    if (!socket || !isConnected) {
        showNotification('Not connected to server. Please wait...', 'error');
        return;
    }

    console.log('Sending PVP challenge to:', playerId);
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
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: ' + (type === 'success' ? '#4CAF50' : type === 'error' ? '#F44336' : '#2196F3') + '; color: white; padding: 10px 20px; border-radius: 5px; z-index: 10000; box-shadow: 0 2px 10px rgba(0,0,0,0.3);';
    document.body.appendChild(notification);

    setTimeout(function() {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
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
    console.log('DOM loaded, initializing chat...');
    
    // Initialize SocketIO after a short delay to ensure DOM is ready
    setTimeout(function() {
        initSocketIO();
    }, 200);

    // Set up chat input handler
    var sendButton = document.getElementById('send-chat');
    var inputField = document.getElementById('chat-input');

    if (sendButton) {
        sendButton.addEventListener('click', function(e) {
            e.preventDefault();
            sendChatMessage();
        });
    }

    if (inputField) {
        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
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
        refreshButton.addEventListener('click', function(e) {
            e.preventDefault();
            refreshPlayerList();
        });
    }

    // If already connected, re-join to update player name
    if (isConnected && socket) {
        socket.emit('join', {
            room: currentRoom, 
            location_room: locationRoom, 
            player_name: playerName
        });
    }
});

// Export functions for global access
window.sendChatMessage = sendChatMessage;
window.refreshPlayerList = refreshPlayerList;
window.challengePlayer = challengePlayer;
window.handleCommand = handleCommand;
window.updateConnectionStatus = updateConnectionStatus;
