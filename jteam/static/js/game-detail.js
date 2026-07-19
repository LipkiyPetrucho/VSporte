(function () {
    function getCsrfToken() {
        if (typeof Cookies !== 'undefined') {
            return Cookies.get('csrftoken');
        }
        return '';
    }

    function initMenu() {
        const menuBtn = document.getElementById('game-view-menu-btn');
        const dropdown = document.getElementById('game-view-menu-dropdown');
        if (!menuBtn || !dropdown) {
            return;
        }

        menuBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            dropdown.classList.toggle('is-open');
        });

        document.addEventListener('click', function () {
            dropdown.classList.remove('is-open');
        });
    }

    function initPlayersPanel() {
        const playersBtn = document.getElementById('game-action-players');
        const panel = document.getElementById('players-panel');
        if (!playersBtn || !panel) {
            return;
        }

        playersBtn.addEventListener('click', function () {
            panel.hidden = !panel.hidden;
        });
    }

    function initManageAction() {
        const manageBtn = document.getElementById('game-action-manage');
        const menuBtn = document.getElementById('game-view-menu-btn');
        if (!manageBtn || !menuBtn) {
            return;
        }

        manageBtn.addEventListener('click', function () {
            menuBtn.click();
        });
    }

    function initMap() {
        if (typeof ymaps === 'undefined' || !window.gameDetailMapConfig) {
            return;
        }

        const config = window.gameDetailMapConfig;
        ymaps.ready(function () {
            const map = new ymaps.Map('map', {
                center: [config.lat, config.lng],
                zoom: 17,
                controls: ['zoomControl'],
            });

            map.geoObjects.add(new ymaps.Placemark([config.lat, config.lng], {
                balloonContent: config.place,
            }, {
                preset: 'islands#greenDotIcon',
            }));
        });
    }

    function renderParticipantPreview(players, currentUsername, organizerUsername) {
        const preview = document.getElementById('participants-preview');
        if (!preview) {
            return;
        }

        if (!players.length) {
            preview.innerHTML = '<p class="game-view-empty">Пока нет участников. Будьте первым!</p>';
            return;
        }

        preview.innerHTML = players.map(function (player) {
            return buildParticipantRow(
                player,
                player.username === currentUsername,
                player.username === organizerUsername
            );
        }).join('');
    }

    function playerProfileUrl(player) {
        if (player.url) {
            return player.url;
        }
        return '/users/' + encodeURIComponent(player.username) + '/';
    }

    function buildParticipantRow(player, isCurrentUser, isOrganizer) {
        const avatar = player.photo
            ? '<img src="' + player.photo + '" alt="" class="game-view-participant-avatar">'
            : '<span class="game-view-participant-avatar placeholder">' + player.username.charAt(0).toUpperCase() + '</span>';

        const profileUrl = playerProfileUrl(player);
        const name = isCurrentUser
            ? '<span class="game-view-participant-name">Вы</span>'
            : '<a href="' + profileUrl + '" class="game-view-participant-name">' + player.username + '</a>';

        const badge = isOrganizer ? '<span class="game-view-badge">Организатор</span>' : '';

        return (
            '<div class="game-view-participant">' +
                avatar +
                '<div>' + name + badge + '</div>' +
            '</div>'
        );
    }

    function renderPlayersList(players) {
        const list = document.getElementById('players-list');
        if (!list) {
            return;
        }

        if (!players.length) {
            list.innerHTML = '<p class="game-view-empty">Пока нет игроков.</p>';
            return;
        }

        list.innerHTML = '<div class="game-view-players-grid"></div>';
        const grid = list.querySelector('.game-view-players-grid');

        players.forEach(function (player) {
            const avatar = player.photo
                ? '<img src="' + player.photo + '" alt="" class="game-view-participant-avatar">'
                : '<span class="game-view-participant-avatar placeholder">' + player.username.charAt(0).toUpperCase() + '</span>';

            const profileUrl = playerProfileUrl(player);
            grid.insertAdjacentHTML('beforeend',
                '<div class="game-view-player-card">' +
                    avatar +
                    '<a href="' + profileUrl + '">' + player.username + '</a>' +
                '</div>'
            );
        });
    }

    function updateJoinButton(btn, action, gameId) {
        if (!btn) {
            return;
        }

        btn.dataset.action = action;
        btn.classList.remove('game-view-action--invite', 'game-view-action--pending');

        if (gameId && action !== 'accept_invitation') {
            btn.dataset.id = gameId;
        }

        if (action === 'leave') {
            btn.classList.add('danger');
            btn.removeAttribute('title');
            btn.innerHTML =
                '<span class="game-view-action-icon"><i class="fas fa-times"></i></span>Выйти';
        } else if (action === 'cancel_request') {
            btn.classList.remove('danger');
            btn.classList.add('game-view-action--pending');
            btn.title = 'Нажмите, чтобы отменить заявку';
            btn.innerHTML =
                '<span class="game-view-action-icon"><i class="fas fa-clock"></i></span>Заявка отправлена';
        } else if (action === 'accept_invitation') {
            btn.classList.remove('danger');
            btn.classList.add('game-view-action--invite');
            btn.removeAttribute('title');
            btn.innerHTML =
                '<span class="game-view-action-icon"><i class="fas fa-envelope-open"></i></span>Принять приглашение';
        } else {
            btn.classList.remove('danger');
            btn.removeAttribute('title');
            btn.innerHTML =
                '<span class="game-view-action-icon"><i class="fas fa-plus"></i></span>Войти';
        }
    }

    function participationStatusToAction(status) {
        if (status === 'joined') {
            return 'leave';
        }
        if (status === 'invited') {
            return 'accept_invitation';
        }
        if (status === 'pending') {
            return 'cancel_request';
        }
        return 'join';
    }

    function initJoinLeave() {
        const root = document.querySelector('.game-view');
        const joinBtn = document.getElementById('join-btn');
        if (!root || !joinBtn) {
            return;
        }

        const joinUrl = root.dataset.joinUrl;
        const gameId = root.dataset.gameId;
        const organizerUsername = root.dataset.organizerUsername || '';
        const currentUsername = root.dataset.currentUsername || '';

        document.addEventListener('click', async function (event) {
            const btn = event.target.closest('#join-btn');
            if (!btn) {
                return;
            }

            event.preventDefault();
            const action = btn.dataset.action;

            if (action === 'accept_invitation') {
                const inviteUrl = root.dataset.inviteUrl;
                const body = new FormData();
                body.append('id', btn.dataset.id);
                body.append('action', 'accept');

                const response = await fetch(inviteUrl, {
                    method: 'POST',
                    mode: 'same-origin',
                    headers: { 'X-CSRFToken': getCsrfToken() },
                    body: body,
                });

                const data = await response.json();
                if (data.status !== 'ok') {
                    alert(data.message || 'Не удалось принять приглашение');
                    return;
                }

                const countNode = document.getElementById('players-count');
                if (countNode) {
                    countNode.textContent = data.players_count;
                }

                renderParticipantPreview(data.players, currentUsername, organizerUsername);
                renderPlayersList(data.players);
                updateJoinButton(
                    btn,
                    participationStatusToAction(data.participation_status),
                    gameId
                );

                const declineBtn = document.getElementById('decline-invite-btn');
                if (declineBtn) {
                    declineBtn.remove();
                }
                return;
            }

            const body = new FormData();
            body.append('id', btn.dataset.id);
            body.append('action', action);

            const response = await fetch(joinUrl, {
                method: 'POST',
                mode: 'same-origin',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: body,
            });

            const data = await response.json();
            if (data.status !== 'ok') {
                alert(data.message || 'Не удалось обновить участие');
                return;
            }

            const countNode = document.getElementById('players-count');
            if (countNode) {
                countNode.textContent = data.players_count;
            }

            renderParticipantPreview(data.players, currentUsername, organizerUsername);
            renderPlayersList(data.players);
            updateJoinButton(
                btn,
                data.participation_status
                    ? participationStatusToAction(data.participation_status)
                    : (action === 'join' ? 'cancel_request' : 'join'),
                gameId
            );
        });
    }

    function appendPendingInvitation(invitationId, username, avatarHtml, profileUrl) {
        let block = document.getElementById('pending-invitations-block');
        if (!block) {
            const anchor = document.getElementById('participation-requests-block')
                || document.getElementById('players-panel');
            if (!anchor) {
                return;
            }
            anchor.insertAdjacentHTML(
                anchor.id === 'players-panel' ? 'afterend' : 'beforebegin',
                '<div class="game-view-requests game-view-invitations" id="pending-invitations-block">' +
                    '<h3 class="game-view-card-title">Отправленные приглашения</h3>' +
                    '<ul class="game-view-requests-list" id="pending-invitations-list"></ul>' +
                '</div>'
            );
            block = document.getElementById('pending-invitations-block');
        }

        const list = document.getElementById('pending-invitations-list');
        if (!list) {
            return;
        }

        list.insertAdjacentHTML('beforeend',
            '<li class="game-view-request">' +
                '<div class="game-view-request-user">' +
                    avatarHtml +
                    '<a href="' + profileUrl + '" class="game-view-participant-name">' + username + '</a>' +
                '</div>' +
                '<div class="game-view-request-actions">' +
                    '<button type="button" class="game-view-request-btn reject" ' +
                        'data-invitation-id="' + invitationId + '" data-action="cancel">Отменить</button>' +
                '</div>' +
            '</li>'
        );
    }

    function initParticipationActions() {
        const root = document.querySelector('.game-view');
        if (!root) {
            return;
        }

        const participationUrl = root.dataset.participationUrl;
        if (!participationUrl) {
            return;
        }

        const organizerUsername = root.dataset.organizerUsername || '';
        const currentUsername = root.dataset.currentUsername || '';

        document.addEventListener('click', async function (event) {
            const btn = event.target.closest('[data-participation-id]');
            if (!btn) {
                return;
            }

            event.preventDefault();
            const body = new FormData();
            body.append('id', btn.dataset.participationId);
            body.append('action', btn.dataset.action);

            const response = await fetch(participationUrl, {
                method: 'POST',
                mode: 'same-origin',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: body,
            });

            const data = await response.json();
            if (data.status !== 'ok') {
                alert(data.message || 'Не удалось обработать заявку');
                return;
            }

            const requestItem = btn.closest('.game-view-request');
            if (requestItem) {
                requestItem.remove();
            }

            const requestsList = document.getElementById('participation-requests-list');
            if (requestsList && !requestsList.children.length) {
                const requestsBlock = document.getElementById('participation-requests-block');
                if (requestsBlock) {
                    requestsBlock.remove();
                }
            }

            if (data.players) {
                const countNode = document.getElementById('players-count');
                if (countNode) {
                    countNode.textContent = data.players_count;
                }
                renderParticipantPreview(data.players, currentUsername, organizerUsername);
                renderPlayersList(data.players);
            }
        });
    }

    function initInvitationActions() {
        const root = document.querySelector('.game-view');
        if (!root) {
            return;
        }

        const inviteUrl = root.dataset.inviteUrl;
        if (!inviteUrl) {
            return;
        }

        const gameId = root.dataset.gameId;
        const organizerUsername = root.dataset.organizerUsername || '';
        const currentUsername = root.dataset.currentUsername || '';

        document.addEventListener('click', async function (event) {
            const declineBtn = event.target.closest('#decline-invite-btn');
            if (declineBtn) {
                event.preventDefault();
                const body = new FormData();
                body.append('id', declineBtn.dataset.id);
                body.append('action', 'decline');

                const response = await fetch(inviteUrl, {
                    method: 'POST',
                    mode: 'same-origin',
                    headers: { 'X-CSRFToken': getCsrfToken() },
                    body: body,
                });

                const data = await response.json();
                if (data.status !== 'ok') {
                    alert(data.message || 'Не удалось отклонить приглашение');
                    return;
                }

                declineBtn.remove();
                const joinBtn = document.getElementById('join-btn');
                if (joinBtn) {
                    updateJoinButton(joinBtn, 'join', gameId);
                }
                return;
            }

            const cancelBtn = event.target.closest('[data-invitation-id][data-action="cancel"]');
            if (!cancelBtn) {
                return;
            }

            event.preventDefault();
            const body = new FormData();
            body.append('id', cancelBtn.dataset.invitationId);
            body.append('action', 'cancel');

            const response = await fetch(inviteUrl, {
                method: 'POST',
                mode: 'same-origin',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: body,
            });

            const data = await response.json();
            if (data.status !== 'ok') {
                alert(data.message || 'Не удалось отменить приглашение');
                return;
            }

            const invitationItem = cancelBtn.closest('.game-view-request');
            if (invitationItem) {
                invitationItem.remove();
            }

            const invitationsList = document.getElementById('pending-invitations-list');
            if (invitationsList && !invitationsList.children.length) {
                const invitationsBlock = document.getElementById('pending-invitations-block');
                if (invitationsBlock) {
                    invitationsBlock.remove();
                }
            }
        });
    }

    function initInviteModal() {
        const root = document.querySelector('.game-view');
        const addBtn = document.getElementById('game-action-add');
        const modal = document.getElementById('game-invite-modal');
        if (!root || !addBtn || !modal) {
            return;
        }

        const inviteUrl = root.dataset.inviteUrl;
        const gameId = root.dataset.gameId;
        const closeBtn = document.getElementById('game-invite-close');
        const backdrop = document.getElementById('game-invite-backdrop');

        function openModal() {
            modal.hidden = false;
            document.body.classList.add('game-invite-modal-open');
        }

        function closeModal() {
            modal.hidden = true;
            document.body.classList.remove('game-invite-modal-open');
        }

        addBtn.addEventListener('click', function () {
            openModal();
        });

        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }
        if (backdrop) {
            backdrop.addEventListener('click', closeModal);
        }

        modal.addEventListener('click', async function (event) {
            const inviteBtn = event.target.closest('[data-user-id][data-action="invite"]');
            if (!inviteBtn || inviteBtn.disabled) {
                return;
            }

            event.preventDefault();
            inviteBtn.disabled = true;

            const body = new FormData();
            body.append('action', 'invite');
            body.append('game_id', gameId);
            body.append('to_user_id', inviteBtn.dataset.userId);

            const response = await fetch(inviteUrl, {
                method: 'POST',
                mode: 'same-origin',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: body,
            });

            const data = await response.json();
            if (data.status !== 'ok') {
                alert(data.message || 'Не удалось отправить приглашение');
                inviteBtn.disabled = false;
                return;
            }

            const inviteItem = inviteBtn.closest('.game-view-invite-item');
            if (inviteItem) {
                const usernameNode = inviteItem.querySelector('.game-view-participant-name');
                const avatarNode = inviteItem.querySelector('.game-view-participant-avatar');
                const username = usernameNode ? usernameNode.textContent.trim() : '';
                const avatarHtml = avatarNode ? avatarNode.outerHTML : '';
                const profileUrl = '/users/' + encodeURIComponent(username) + '/';

                inviteItem.remove();

                if (data.invitation_id && username) {
                    appendPendingInvitation(
                        data.invitation_id,
                        username,
                        avatarHtml,
                        profileUrl
                    );
                }
            }

            const inviteList = document.getElementById('game-invite-list');
            if (inviteList && !inviteList.children.length) {
                const emptyNode = document.getElementById('game-invite-empty');
                if (!emptyNode) {
                    const dialog = modal.querySelector('.game-view-invite-dialog');
                    if (dialog) {
                        dialog.insertAdjacentHTML(
                            'beforeend',
                            '<p class="game-view-empty" id="game-invite-empty">Нет друзей для приглашения</p>'
                        );
                    }
                }
            }

            closeModal();
        });
    }

    function initChatButtons() {
        document.querySelectorAll('[data-game-chat-btn]').forEach(function (button) {
            button.addEventListener('click', function () {
                alert('Чат скоро будет доступен');
            });
        });
    }

    const STATUS_MESSAGES = {
        started: 'Игра уже началась',
        finished: 'Игра уже закончилась',
    };
    const STATUS_POLL_INTERVAL_MS = 10000;

    function updateStatusBadge(element, status, label) {
        if (!element) {
            return;
        }
        element.textContent = label;
        element.classList.remove('status-open', 'status-started', 'status-finished');
        element.classList.add('status-' + status);
    }

    function applyGameStatus(root, status, label) {
        root.dataset.gameStatus = status;
        updateStatusBadge(document.getElementById('game-header-status'), status, label);
        updateStatusBadge(document.getElementById('game-details-status'), status, label);

        const messageEl = document.getElementById('game-status-message');
        if (messageEl) {
            const message = STATUS_MESSAGES[status] || '';
            messageEl.textContent = message;
            messageEl.style.display = message ? '' : 'none';
        }

        if (status !== 'open') {
            ['join-btn', 'decline-invite-btn', 'game-action-add'].forEach(function (id) {
                const button = document.getElementById(id);
                if (button) {
                    button.disabled = true;
                }
            });
        }
    }

    function initStatusPolling() {
        const root = document.querySelector('.game-view');
        if (!root || !root.dataset.statusUrl) {
            return;
        }

        let currentStatus = root.dataset.gameStatus || 'open';
        if (currentStatus === 'finished') {
            return;
        }

        let timerId = null;

        function pollStatus() {
            if (document.hidden) {
                return;
            }

            fetch(root.dataset.statusUrl, {
                headers: { 'Accept': 'application/json' },
                credentials: 'same-origin',
            })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('status poll failed');
                    }
                    return response.json();
                })
                .then(function (data) {
                    if (!data || !data.status) {
                        return;
                    }
                    if (data.status !== currentStatus) {
                        currentStatus = data.status;
                        applyGameStatus(root, data.status, data.label);
                    }
                    if (data.status === 'finished' && timerId !== null) {
                        clearInterval(timerId);
                        timerId = null;
                    }
                })
                .catch(function () {
                    // Тихий сбой: следующий опрос через интервал
                });
        }

        timerId = setInterval(pollStatus, STATUS_POLL_INTERVAL_MS);
        document.addEventListener('visibilitychange', function () {
            if (!document.hidden && currentStatus !== 'finished') {
                pollStatus();
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initMenu();
        initPlayersPanel();
        initManageAction();
        initMap();
        initJoinLeave();
        initParticipationActions();
        initInvitationActions();
        initInviteModal();
        initChatButtons();
        initStatusPolling();
    });
})();
