(function () {
    'use strict';

    var RECONNECT_BASE_MS = 1000;
    var RECONNECT_MAX_MS = 30000;

    function scrollChatToBottom(body) {
        if (!body) {
            return;
        }
        body.scrollTop = body.scrollHeight;
    }

    function escapeText(value) {
        return value == null ? '' : String(value);
    }

    function formatMessageTime(iso) {
        var date = new Date(iso);
        if (Number.isNaN(date.getTime())) {
            return '';
        }
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
        });
    }

    function buildWsUrl(gameId) {
        var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return protocol + '//' + window.location.host + '/ws/games/' + gameId + '/chat/';
    }

    function initGameChat() {
        var root = document.querySelector('.game-chat');
        if (!root) {
            return;
        }

        var gameId = root.getAttribute('data-game-id');
        if (!gameId) {
            return;
        }

        var body = root.querySelector('[data-chat-body]');
        var list = root.querySelector('[data-chat-list]');
        var empty = root.querySelector('[data-chat-empty]');
        var form = root.querySelector('[data-chat-form]');
        var input = root.querySelector('[data-chat-input]');
        var sendBtn = root.querySelector('[data-chat-send]');

        var socket = null;
        var reconnectAttempt = 0;
        var reconnectTimer = null;
        var intentionalClose = false;

        scrollChatToBottom(body);
        updateEmptyState();

        function setConnected(isConnected) {
            if (sendBtn) {
                sendBtn.disabled = !isConnected;
            }
            if (input) {
                input.disabled = !isConnected;
            }
        }

        function updateEmptyState() {
            if (!empty || !list) {
                return;
            }
            var hasMessages = list.querySelector('[data-message-id]');
            empty.classList.toggle('is-hidden', Boolean(hasMessages));
        }

        function hasMessage(messageId) {
            if (!list || messageId == null) {
                return false;
            }
            return Boolean(list.querySelector('[data-message-id="' + messageId + '"]'));
        }

        function createAvatar(author) {
            var link = document.createElement('a');
            link.className = 'game-chat-avatar';
            link.href = author.url || '#';
            link.tabIndex = -1;

            if (author.photo) {
                var img = document.createElement('img');
                img.src = author.photo;
                img.alt = '';
                link.appendChild(img);
            } else {
                var placeholder = document.createElement('span');
                placeholder.className = 'game-chat-avatar-placeholder';
                var username = escapeText(author.username);
                placeholder.textContent = username ? username.charAt(0).toUpperCase() : '?';
                link.appendChild(placeholder);
            }
            return link;
        }

        function appendMessage(payload) {
            if (!list || !payload || payload.id == null) {
                return;
            }
            if (hasMessage(payload.id)) {
                return;
            }

            var isOwn = Boolean(payload.is_own);
            var author = payload.author || {};
            var item = document.createElement('li');
            item.className = 'game-chat-item' + (isOwn ? ' game-chat-item--own' : '');
            item.setAttribute('data-message-id', String(payload.id));

            if (!isOwn) {
                item.appendChild(createAvatar(author));
            }

            var bubble = document.createElement('div');
            bubble.className = 'game-chat-bubble';

            if (!isOwn) {
                var authorEl = document.createElement('div');
                authorEl.className = 'game-chat-author';
                authorEl.textContent = escapeText(author.username);
                bubble.appendChild(authorEl);
            }

            var textEl = document.createElement('div');
            textEl.className = 'game-chat-text';
            textEl.textContent = escapeText(payload.text);
            bubble.appendChild(textEl);

            var timeEl = document.createElement('time');
            timeEl.className = 'game-chat-time';
            if (payload.created_at) {
                timeEl.setAttribute('datetime', payload.created_at);
                timeEl.textContent = formatMessageTime(payload.created_at);
            }
            bubble.appendChild(timeEl);

            item.appendChild(bubble);
            list.appendChild(item);
            updateEmptyState();
            scrollChatToBottom(body);
        }

        function clearReconnectTimer() {
            if (reconnectTimer !== null) {
                window.clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        }

        function scheduleReconnect() {
            clearReconnectTimer();
            var delay = Math.min(
                RECONNECT_BASE_MS * Math.pow(2, reconnectAttempt),
                RECONNECT_MAX_MS
            );
            reconnectAttempt += 1;
            reconnectTimer = window.setTimeout(connect, delay);
        }

        function handleSocketMessage(event) {
            var data;
            try {
                data = JSON.parse(event.data);
            } catch (err) {
                return;
            }

            if (!data || !data.type) {
                return;
            }

            if (data.type === 'chat.message') {
                appendMessage(data);
                return;
            }

            if (data.type === 'error' && data.message && input) {
                input.setCustomValidity(data.message);
                input.reportValidity();
                input.setCustomValidity('');
            }
        }

        function connect() {
            clearReconnectTimer();

            if (
                socket &&
                (socket.readyState === WebSocket.OPEN ||
                    socket.readyState === WebSocket.CONNECTING)
            ) {
                return;
            }

            setConnected(false);
            socket = new WebSocket(buildWsUrl(gameId));

            socket.addEventListener('open', function () {
                reconnectAttempt = 0;
                setConnected(true);
            });

            socket.addEventListener('message', handleSocketMessage);

            socket.addEventListener('close', function () {
                setConnected(false);
                socket = null;
                if (!intentionalClose) {
                    scheduleReconnect();
                }
            });

            socket.addEventListener('error', function () {
                // close сработает следом и запустит reconnect
                if (socket) {
                    socket.close();
                }
            });
        }

        function sendMessage(text) {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                return false;
            }
            socket.send(JSON.stringify({
                type: 'chat.message',
                text: text,
            }));
            return true;
        }

        if (form) {
            form.addEventListener('submit', function (event) {
                event.preventDefault();
                if (!input) {
                    return;
                }
                var text = (input.value || '').trim();
                if (!text) {
                    return;
                }
                if (sendMessage(text)) {
                    input.value = '';
                    input.focus();
                }
            });
        }

        if (input) {
            input.addEventListener('keydown', function (event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    if (form) {
                        form.dispatchEvent(new Event('submit', {
                            cancelable: true,
                            bubbles: true,
                        }));
                    }
                }
            });
        }

        window.addEventListener('beforeunload', function () {
            intentionalClose = true;
            clearReconnectTimer();
            if (socket) {
                socket.close();
            }
        });

        connect();
    }

    document.addEventListener('DOMContentLoaded', initGameChat);
})();
