(function () {
    let playerTeamMap = {};
    let currentTeamRoster = null;
    let selectedTeamChip = null;
    let teamsAssignBusy = false;

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
            if (!panel.hidden) {
                const teamsPanel = document.getElementById('teams-panel');
                if (teamsPanel) {
                    teamsPanel.hidden = true;
                }
            }
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

    function renderParticipantPreview(players, currentUsername, organizerUsername, extraPlayers) {
        const preview = document.getElementById('participants-preview');
        if (!preview) {
            return;
        }

        const root = document.querySelector('.game-view');
        const extras = Math.max(
            0,
            parseInt(
                extraPlayers != null
                    ? extraPlayers
                    : ((root && root.dataset.extraPlayers) || '0'),
                10
            ) || 0
        );

        if (!players.length && extras === 0) {
            preview.innerHTML = '<p class="game-view-empty">Пока нет участников. Будьте первым!</p>';
            return;
        }

        if (!players.length && extras > 0) {
            preview.innerHTML =
                '<div class="game-view-participant game-view-participant--organizer">' +
                    '<span class="game-view-extra-count" id="extra-players-badge">+' + extras + '</span>' +
                    '<span class="game-view-participant-name game-view-participant-name--muted">офлайн</span>' +
                '</div>';
            return;
        }

        preview.innerHTML = players.map(function (player) {
            return buildParticipantRow(
                player,
                player.username === currentUsername,
                player.username === organizerUsername,
                extras
            );
        }).join('');
    }

    function updateOccupiedCount(joinedCount, extraPlayers, maxPlayers) {
        const root = document.querySelector('.game-view');
        const extras = Math.max(
            0,
            parseInt(
                extraPlayers != null
                    ? extraPlayers
                    : ((root && root.dataset.extraPlayers) || '0'),
                10
            ) || 0
        );
        const joined = Math.max(0, parseInt(joinedCount, 10) || 0);
        const occupied = joined + extras;

        const countNode = document.getElementById('players-count');
        if (countNode) {
            countNode.textContent = String(occupied);
        }

        if (maxPlayers != null) {
            const maxNode = document.getElementById('players-max');
            if (maxNode) {
                maxNode.textContent = String(maxPlayers);
            }
            if (root) {
                root.dataset.maxPlayers = String(maxPlayers);
            }
        }

        if (root) {
            root.dataset.extraPlayers = String(extras);
            if (typeof joinedCount !== 'undefined' && joinedCount != null) {
                root.dataset.joinedCount = String(joined);
            }
        }

        return occupied;
    }

    function syncExtraPlayersBadge(extraCount) {
        const extras = Math.max(0, parseInt(extraCount, 10) || 0);
        const preview = document.getElementById('participants-preview');
        let badge = document.getElementById('extra-players-badge');

        if (extras <= 0) {
            if (badge) {
                badge.hidden = true;
                badge.textContent = '+0';
            }
            return;
        }

        if (!badge && preview) {
            const organizerRow = preview.querySelector('.game-view-participant--organizer .game-view-participant-meta');
            if (organizerRow) {
                organizerRow.insertAdjacentHTML(
                    'beforeend',
                    '<span class="game-view-extra-count" id="extra-players-badge"></span>'
                );
                badge = document.getElementById('extra-players-badge');
            }
        }

        if (badge) {
            badge.hidden = false;
            badge.textContent = '+' + extras;
        }
    }

    function syncParticipantsFromResponse(data, currentUsername, organizerUsername) {
        const joined = data.joined_count != null
            ? data.joined_count
            : (data.players ? data.players.length : data.players_count);
        const extras = data.extra_players;
        updateOccupiedCount(joined, extras, data.max_players);
        if (data.available_seats != null) {
            const root = document.querySelector('.game-view');
            if (root) {
                root.dataset.availableSeats = String(data.available_seats);
            }
            const availableEl = document.getElementById('organizer-available-seats');
            if (availableEl) {
                availableEl.textContent = String(data.available_seats);
            }
        }
        if (data.team_roster) {
            playerTeamMap = buildPlayerTeamMap(normalizeTeamRoster(data.team_roster));
        }
        if (data.players) {
            renderParticipantPreview(
                data.players,
                currentUsername,
                organizerUsername,
                extras
            );
            renderPlayersList(data.players);
        } else {
            syncExtraPlayersBadge(extras);
        }
        if (data.team_roster) {
            applyTeamRoster(data.team_roster);
        }
    }

    function playerProfileUrl(player) {
        if (player.url) {
            return player.url;
        }
        return '/users/' + encodeURIComponent(player.username) + '/';
    }

    function teamBadgeHtml(team) {
        if (team === 1) {
            return '<span class="game-view-team-badge game-view-team-badge--a" title="Команда A" aria-label="Команда A">A</span>';
        }
        if (team === 2) {
            return '<span class="game-view-team-badge game-view-team-badge--b" title="Команда B" aria-label="Команда B">B</span>';
        }
        return '';
    }

    function buildParticipantRow(player, isCurrentUser, isOrganizer, extraPlayers) {
        const avatar = player.photo
            ? '<img src="' + player.photo + '" alt="" class="game-view-participant-avatar">'
            : '<span class="game-view-participant-avatar placeholder">' + player.username.charAt(0).toUpperCase() + '</span>';

        const profileUrl = playerProfileUrl(player);
        const name = isCurrentUser
            ? '<span class="game-view-participant-name">Вы</span>'
            : '<a href="' + profileUrl + '" class="game-view-participant-name">' + player.username + '</a>';

        const teamBadge = teamBadgeHtml(playerTeamMap[player.username]);
        const badge = isOrganizer ? '<span class="game-view-badge">Организатор</span>' : '';
        const extras = Math.max(0, parseInt(extraPlayers, 10) || 0);
        const extraBadge = isOrganizer
            ? (
                '<span class="game-view-extra-count" id="extra-players-badge"' +
                (extras > 0 ? '' : ' hidden') +
                '>+' + extras + '</span>'
            )
            : '';

        return (
            '<div class="game-view-participant' + (isOrganizer ? ' game-view-participant--organizer' : '') + '">' +
                avatar +
                '<div class="game-view-participant-meta">' + name + teamBadge + badge + extraBadge + '</div>' +
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

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function normalizeTeamRoster(roster) {
        if (!roster || typeof roster !== 'object') {
            return { teams: { 1: [], 2: [] }, bench: [] };
        }
        const teams = roster.teams || {};
        return {
            teams: {
                1: teams[1] || teams['1'] || [],
                2: teams[2] || teams['2'] || [],
            },
            bench: roster.bench || [],
        };
    }

    function buildPlayerTeamMap(roster) {
        const map = {};
        const normalized = normalizeTeamRoster(roster);
        [1, 2].forEach(function (team) {
            (normalized.teams[team] || []).forEach(function (entry) {
                if (entry && entry.type === 'user' && entry.username) {
                    map[entry.username] = team;
                }
            });
        });
        return map;
    }

    function chipKey(entry) {
        if (!entry) {
            return '';
        }
        if (entry.type === 'user') {
            return 'user:' + entry.user_id;
        }
        return 'offline:' + entry.offline_slot;
    }

    function entryLabel(entry) {
        if (!entry) {
            return '';
        }
        if (entry.type === 'offline') {
            return entry.label || ('Гость ' + (Number(entry.offline_slot) + 1));
        }
        return entry.username || '';
    }

    function entryInitial(entry) {
        const label = entryLabel(entry);
        return label ? label.charAt(0).toUpperCase() : '?';
    }

    function buildTeamChip(entry, team, editable) {
        const key = chipKey(entry);
        const label = escapeHtml(entryLabel(entry));
        const isOffline = entry.type === 'offline';
        const avatar = (!isOffline && entry.photo)
            ? '<img src="' + escapeHtml(entry.photo) + '" alt="" class="game-teams-chip__avatar">'
            : (
                '<span class="game-teams-chip__avatar game-teams-chip__avatar--placeholder' +
                (isOffline ? ' game-teams-chip__avatar--guest' : '') +
                '">' + escapeHtml(entryInitial(entry)) + '</span>'
            );

        const attrs = [
            'class="game-teams-chip' +
                (team === 1 ? ' game-teams-chip--a' : '') +
                (team === 2 ? ' game-teams-chip--b' : '') +
                (isOffline ? ' game-teams-chip--guest' : '') +
                '"',
            'type="button"',
            'data-chip-key="' + escapeHtml(key) + '"',
            'data-entry-type="' + escapeHtml(entry.type) + '"',
            team ? 'data-current-team="' + team + '"' : 'data-current-team=""',
        ];

        if (entry.type === 'user') {
            attrs.push('data-user-id="' + escapeHtml(entry.user_id) + '"');
        } else {
            attrs.push('data-offline-slot="' + escapeHtml(entry.offline_slot) + '"');
        }

        if (!editable) {
            attrs.push('disabled');
            attrs.push('tabindex="-1"');
        }

        return (
            '<button ' + attrs.join(' ') + '>' +
                avatar +
                '<span class="game-teams-chip__name">' + label + '</span>' +
            '</button>'
        );
    }

    function emptySlotHtml(count) {
        let html = '';
        const slots = Math.max(1, count);
        for (let i = 0; i < slots; i += 1) {
            html += '<span class="game-teams-empty-slot" aria-hidden="true"></span>';
        }
        return html;
    }

    function renderTeamSlots(container, entries, team, editable) {
        if (!container) {
            return;
        }
        const list = entries || [];
        if (!list.length) {
            container.innerHTML = emptySlotHtml(2);
            return;
        }
        container.innerHTML = list.map(function (entry) {
            return buildTeamChip(entry, team, editable);
        }).join('') + emptySlotHtml(1);
    }

    function renderTeamBench(container, entries, editable) {
        if (!container) {
            return;
        }
        const list = entries || [];
        if (!list.length) {
            container.innerHTML = '<p class="game-teams-bench__empty">Все игроки распределены</p>';
            return;
        }
        container.innerHTML = list.map(function (entry) {
            return buildTeamChip(entry, null, editable);
        }).join('');
    }

    function syncParticipantTeamBadges() {
        const preview = document.getElementById('participants-preview');
        if (!preview) {
            return;
        }

        preview.querySelectorAll('.game-view-participant').forEach(function (row) {
            const nameLink = row.querySelector('.game-view-participant-name');
            if (!nameLink) {
                return;
            }
            const username = nameLink.tagName === 'A'
                ? nameLink.textContent.trim()
                : null;
            const isYou = nameLink.tagName === 'SPAN' && nameLink.textContent.trim() === 'Вы';
            const root = document.querySelector('.game-view');
            const currentUsername = root ? (root.dataset.currentUsername || '') : '';
            const key = isYou ? currentUsername : username;
            const team = key ? playerTeamMap[key] : null;

            let badge = row.querySelector('.game-view-team-badge');
            if (!team) {
                if (badge) {
                    badge.remove();
                }
                return;
            }

            const html = teamBadgeHtml(team);
            if (badge) {
                badge.outerHTML = html;
            } else {
                const meta = row.querySelector('.game-view-participant-meta');
                if (meta) {
                    nameLink.insertAdjacentHTML('afterend', html);
                }
            }
        });
    }

    function showTeamsStatus(message, isError) {
        const statusEl = document.getElementById('teams-status');
        if (!statusEl) {
            return;
        }
        if (!message) {
            statusEl.hidden = true;
            statusEl.textContent = '';
            statusEl.classList.remove('is-error');
            return;
        }
        statusEl.hidden = false;
        statusEl.textContent = message;
        statusEl.classList.toggle('is-error', !!isError);
    }

    function clearTeamSelection() {
        selectedTeamChip = null;
        document.querySelectorAll('.game-teams-chip.is-selected').forEach(function (el) {
            el.classList.remove('is-selected');
        });
        document.querySelectorAll('.game-teams-side.is-target, .game-teams-bench.is-target').forEach(function (el) {
            el.classList.remove('is-target');
        });
    }

    function setTeamSelection(chipEl) {
        clearTeamSelection();
        if (!chipEl) {
            return;
        }
        selectedTeamChip = {
            type: chipEl.dataset.entryType,
            user_id: chipEl.dataset.userId ? parseInt(chipEl.dataset.userId, 10) : null,
            offline_slot: chipEl.dataset.offlineSlot != null && chipEl.dataset.offlineSlot !== ''
                ? parseInt(chipEl.dataset.offlineSlot, 10)
                : null,
            current_team: chipEl.dataset.currentTeam
                ? parseInt(chipEl.dataset.currentTeam, 10)
                : null,
            key: chipEl.dataset.chipKey,
        };
        chipEl.classList.add('is-selected');
        document.querySelectorAll('.game-teams-side, .game-teams-bench').forEach(function (zone) {
            zone.classList.add('is-target');
        });
    }

    function applyTeamRoster(roster, options) {
        const normalized = normalizeTeamRoster(roster);
        currentTeamRoster = normalized;
        playerTeamMap = buildPlayerTeamMap(normalized);

        const panel = document.getElementById('teams-panel');
        if (!panel) {
            syncParticipantTeamBadges();
            return;
        }

        const editable = panel.dataset.editable === '1';
        const animateKey = options && options.animateKey;
        const flashTeam = options && options.flashTeam;

        renderTeamSlots(
            document.getElementById('team-a-slots'),
            normalized.teams[1],
            1,
            editable
        );
        renderTeamSlots(
            document.getElementById('team-b-slots'),
            normalized.teams[2],
            2,
            editable
        );
        renderTeamBench(
            document.getElementById('team-bench'),
            normalized.bench,
            editable
        );

        if (animateKey) {
            const chip = panel.querySelector('[data-chip-key="' + animateKey + '"]');
            if (chip) {
                chip.classList.add('is-pop');
                window.setTimeout(function () {
                    chip.classList.remove('is-pop');
                }, 320);
            }
        }

        if (flashTeam === 1 || flashTeam === 2) {
            const side = panel.querySelector('.game-teams-side[data-team="' + flashTeam + '"]');
            if (side) {
                side.classList.add('is-flash');
                window.setTimeout(function () {
                    side.classList.remove('is-flash');
                }, 420);
            }
        } else if (flashTeam === 'bench') {
            const bench = panel.querySelector('.game-teams-bench');
            if (bench) {
                bench.classList.add('is-flash');
                window.setTimeout(function () {
                    bench.classList.remove('is-flash');
                }, 420);
            }
        }

        syncParticipantTeamBadges();
    }

    function openTeamsPanel() {
        const panel = document.getElementById('teams-panel');
        const playersPanel = document.getElementById('players-panel');
        if (!panel) {
            return;
        }
        if (playersPanel) {
            playersPanel.hidden = true;
        }
        panel.hidden = false;
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    async function assignSelectedToTeam(team) {
        const root = document.querySelector('.game-view');
        const panel = document.getElementById('teams-panel');
        if (!root || !panel || !selectedTeamChip || teamsAssignBusy) {
            return;
        }
        if (panel.dataset.editable !== '1') {
            return;
        }

        const teamsUrl = root.dataset.teamsUrl;
        if (!teamsUrl) {
            return;
        }

        if (selectedTeamChip.current_team === team) {
            clearTeamSelection();
            return;
        }

        const payload = { team: team };
        if (selectedTeamChip.type === 'user') {
            payload.user_id = selectedTeamChip.user_id;
        } else {
            payload.offline_slot = selectedTeamChip.offline_slot;
        }

        const animateKey = selectedTeamChip.key;
        teamsAssignBusy = true;
        showTeamsStatus('');

        try {
            const response = await fetch(teamsUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
                body: JSON.stringify(payload),
            });

            let data = null;
            try {
                data = await response.json();
            } catch (parseError) {
                showTeamsStatus('Не удалось обновить состав', true);
                return;
            }

            if (!response.ok || !data || data.status !== 'ok') {
                showTeamsStatus((data && data.message) || 'Не удалось обновить состав', true);
                return;
            }

            clearTeamSelection();
            applyTeamRoster(data.team_roster, {
                animateKey: animateKey,
                flashTeam: team == null ? 'bench' : team,
            });
        } catch (e) {
            showTeamsStatus('Ошибка сети. Попробуйте ещё раз.', true);
        } finally {
            teamsAssignBusy = false;
        }
    }

    function initTeamsPanel() {
        const root = document.querySelector('.game-view');
        const panel = document.getElementById('teams-panel');
        const teamsBtn = document.getElementById('game-action-teams');
        if (!root || root.dataset.isTeamGame !== '1' || !panel) {
            return;
        }

        const dataEl = document.getElementById('team-roster-data');
        if (dataEl) {
            try {
                applyTeamRoster(JSON.parse(dataEl.textContent));
            } catch (e) {
                applyTeamRoster(null);
            }
        } else {
            applyTeamRoster(null);
        }

        if (teamsBtn) {
            teamsBtn.addEventListener('click', function () {
                if (panel.hidden) {
                    openTeamsPanel();
                } else {
                    panel.hidden = true;
                    clearTeamSelection();
                }
            });
        }

        const organizerTeamsBtn = document.getElementById('organizer-teams-btn');
        if (organizerTeamsBtn) {
            organizerTeamsBtn.addEventListener('click', function () {
                openTeamsPanel();
            });
        }

        panel.addEventListener('click', function (event) {
            if (panel.dataset.editable !== '1') {
                return;
            }

            const chip = event.target.closest('.game-teams-chip');
            if (chip && panel.contains(chip)) {
                event.preventDefault();
                if (selectedTeamChip && selectedTeamChip.key === chip.dataset.chipKey) {
                    clearTeamSelection();
                    return;
                }
                setTeamSelection(chip);
                return;
            }

            if (!selectedTeamChip) {
                return;
            }

            const side = event.target.closest('.game-teams-side[data-team]');
            if (side && panel.contains(side)) {
                event.preventDefault();
                assignSelectedToTeam(parseInt(side.dataset.team, 10));
                return;
            }

            const bench = event.target.closest('.game-teams-bench');
            if (bench && panel.contains(bench)) {
                event.preventDefault();
                assignSelectedToTeam(null);
            }
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

                syncParticipantsFromResponse(data, currentUsername, organizerUsername);
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

            syncParticipantsFromResponse(data, currentUsername, organizerUsername);
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
                syncParticipantsFromResponse(data, currentUsername, organizerUsername);
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

    function initShare() {
        const root = document.querySelector('.game-view');
        const modal = document.getElementById('game-share-modal');
        if (!root || !modal) {
            return;
        }

        const shareUrl = root.dataset.shareUrl || window.location.href;
        const shareText = root.dataset.shareText || '';
        const fullText = shareText ? (shareText + '\n' + shareUrl) : shareUrl;
        const encodedUrl = encodeURIComponent(shareUrl);
        const encodedText = encodeURIComponent(shareText);
        const encodedFull = encodeURIComponent(fullText);

        const telegram = document.getElementById('share-telegram');
        const maxShare = document.getElementById('share-max');
        const whatsapp = document.getElementById('share-whatsapp');
        const vk = document.getElementById('share-vk');
        const ok = document.getElementById('share-ok');
        const copyBtn = document.getElementById('share-copy');
        const copyLabel = document.getElementById('share-copy-label');
        const nativeBtn = document.getElementById('share-native');
        const backdrop = document.getElementById('game-share-backdrop');
        const closeBtn = document.getElementById('game-share-close');

        if (telegram) {
            telegram.href = 'https://t.me/share/url?url=' + encodedUrl + '&text=' + encodedText;
        }
        if (maxShare) {
            maxShare.href = 'https://max.ru/:share?text=' + encodedFull;
        }
        if (whatsapp) {
            whatsapp.href = 'https://wa.me/?text=' + encodedFull;
        }
        if (vk) {
            vk.href = 'https://vk.com/share.php?url=' + encodedUrl + '&title=' + encodedText;
        }
        if (ok) {
            ok.href = 'https://connect.ok.ru/offer?url=' + encodedUrl + '&title=' + encodedText;
        }

        if (nativeBtn && navigator.share) {
            nativeBtn.hidden = false;
            nativeBtn.addEventListener('click', function () {
                navigator.share({
                    title: shareText || document.title,
                    text: shareText,
                    url: shareUrl,
                }).catch(function () {});
            });
        }

        function openShare() {
            const menuDropdown = document.getElementById('game-view-menu-dropdown');
            if (menuDropdown) {
                menuDropdown.classList.remove('is-open');
            }
            modal.hidden = false;
            document.body.classList.add('game-share-modal-open');
        }

        function closeShare() {
            modal.hidden = true;
            document.body.classList.remove('game-share-modal-open');
        }

        ['game-share-btn', 'game-menu-share-btn', 'organizer-share-btn'].forEach(function (id) {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', function (event) {
                    event.preventDefault();
                    event.stopPropagation();
                    openShare();
                });
            }
        });

        if (backdrop) {
            backdrop.addEventListener('click', closeShare);
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', closeShare);
        }

        if (copyBtn) {
            copyBtn.addEventListener('click', function () {
                const done = function () {
                    if (copyLabel) {
                        copyLabel.textContent = 'Ссылка скопирована';
                        setTimeout(function () {
                            copyLabel.textContent = 'Скопировать ссылку';
                        }, 2000);
                    }
                };

                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(shareUrl).then(done).catch(function () {
                        fallbackCopy(shareUrl, done);
                    });
                } else {
                    fallbackCopy(shareUrl, done);
                }
            });
        }

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !modal.hidden) {
                closeShare();
            }
        });
    }

    function fallbackCopy(text, onDone) {
        const input = document.createElement('textarea');
        input.value = text;
        input.setAttribute('readonly', '');
        input.style.position = 'absolute';
        input.style.left = '-9999px';
        document.body.appendChild(input);
        input.select();
        try {
            document.execCommand('copy');
            if (onDone) {
                onDone();
            }
        } catch (e) {
            // ignore
        }
        document.body.removeChild(input);
    }

    function initOrganizerPanel() {
        const root = document.querySelector('.game-view');
        const panel = document.getElementById('game-organizer-panel');
        if (!root || root.dataset.isOrganizer !== '1' || !panel) {
            return;
        }

        const detailsBtn = document.getElementById('organizer-show-details');
        const mapBtn = document.getElementById('organizer-scroll-map');
        const toggleBtn = document.getElementById('organizer-settings-toggle');
        const body = document.getElementById('organizer-settings-body');
        const detailsCard = document.getElementById('game-details-card');
        const mapCard = document.querySelector('.game-view-map-card');
        const form = document.getElementById('organizer-settings-form');

        if (detailsBtn && detailsCard) {
            detailsBtn.addEventListener('click', function () {
                detailsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        if (mapBtn && mapCard) {
            mapBtn.addEventListener('click', function () {
                mapCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        if (toggleBtn && body) {
            toggleBtn.addEventListener('click', function () {
                const collapsed = panel.classList.toggle('is-collapsed');
                toggleBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
                toggleBtn.textContent = collapsed ? 'Показать настройки' : 'Скрыть настройки';
            });
        }

        if (!form) {
            return;
        }

        const stepper = document.getElementById('extra-players-stepper');
        const minusBtn = document.getElementById('extra-players-minus');
        const plusBtn = document.getElementById('extra-players-plus');
        const valueEl = document.getElementById('extra-players-value');
        const inputEl = document.getElementById('extra-players-input');
        const availableEl = document.getElementById('organizer-available-seats');
        const statusEl = document.getElementById('organizer-settings-status');
        const saveBtn = document.getElementById('organizer-settings-save');
        const priceInput = document.getElementById('organizer-price');
        const reservedInput = document.getElementById('organizer-place-reserved');

        let extraPlayers = parseInt(inputEl ? inputEl.value : '0', 10) || 0;
        const maxPlayers = parseInt(root.dataset.maxPlayers || '0', 10) || 0;
        let maxExtra = stepper
            ? (parseInt(stepper.dataset.maxExtra || '0', 10) || 0)
            : 0;

        function currentAvailable() {
            return Math.max(0, maxExtra - extraPlayers);
        }

        function syncStepper() {
            if (valueEl) {
                valueEl.textContent = String(extraPlayers);
            }
            if (inputEl) {
                inputEl.value = String(extraPlayers);
            }
            if (availableEl) {
                availableEl.textContent = String(currentAvailable());
            }
            if (minusBtn) {
                minusBtn.disabled = extraPlayers <= 0;
            }
            if (plusBtn) {
                plusBtn.disabled = extraPlayers >= maxExtra;
            }

            const joinedOnline = parseInt(root.dataset.joinedCount || '', 10);
            const onlineFallback = document.querySelectorAll(
                '#participants-preview .game-view-participant'
            ).length;
            updateOccupiedCount(
                Number.isFinite(joinedOnline) ? joinedOnline : onlineFallback,
                extraPlayers,
                root.dataset.maxPlayers
            );
            syncExtraPlayersBadge(extraPlayers);
        }

        syncStepper();

        if (minusBtn) {
            minusBtn.addEventListener('click', function () {
                if (extraPlayers > 0) {
                    extraPlayers -= 1;
                    syncStepper();
                }
            });
        }

        if (plusBtn) {
            plusBtn.addEventListener('click', function () {
                if (extraPlayers < maxExtra) {
                    extraPlayers += 1;
                    syncStepper();
                }
            });
        }

        function showStatus(message, isError) {
            if (!statusEl) {
                return;
            }
            statusEl.hidden = !message;
            statusEl.textContent = message || '';
            statusEl.classList.toggle('is-error', !!isError);
            statusEl.classList.toggle('is-ok', !isError && !!message);
        }

        form.addEventListener('submit', async function (event) {
            event.preventDefault();
            const settingsUrl = root.dataset.organizerSettingsUrl;
            if (!settingsUrl) {
                return;
            }

            const body = new URLSearchParams();
            body.set('extra_players', String(extraPlayers));
            if (priceInput) {
                body.set('price', priceInput.value || '0');
            }
            if (reservedInput) {
                body.set('place_reserved', reservedInput.checked ? '1' : '0');
            }

            if (saveBtn) {
                saveBtn.disabled = true;
            }
            showStatus('');

            try {
                const response = await fetch(settingsUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    credentials: 'same-origin',
                    body: body,
                });

                let data = null;
                try {
                    data = await response.json();
                } catch (parseError) {
                    showStatus(
                        response.status === 403
                            ? 'Нет прав для изменения'
                            : 'Не удалось сохранить. Обновите страницу.',
                        true
                    );
                    return;
                }

                if (!response.ok || !data || data.status !== 'ok') {
                    showStatus((data && data.message) || 'Не удалось сохранить', true);
                    return;
                }

                extraPlayers = data.extra_players;
                maxExtra = Math.max(0, (data.available_seats || 0) + (data.extra_players || 0));
                if (stepper) {
                    stepper.dataset.maxExtra = String(maxExtra);
                }
                syncStepper();

                updateOccupiedCount(
                    data.joined_count,
                    data.extra_players,
                    data.max_players
                );
                root.dataset.availableSeats = String(data.available_seats);
                syncExtraPlayersBadge(data.extra_players);

                const priceEl = document.getElementById('game-price');
                const totalEl = document.getElementById('game-total-cost');
                if (priceEl && typeof data.price === 'number') {
                    priceEl.textContent = Math.round(data.price) + ' ₽';
                }
                if (totalEl && typeof data.total_cost === 'number') {
                    totalEl.textContent = Math.round(data.total_cost) + ' ₽';
                }

                const note = document.getElementById('game-place-reserved-note');
                if (note && typeof data.place_reserved === 'boolean') {
                    note.textContent = data.place_reserved
                        ? 'Площадка забронирована'
                        : 'Возможно площадка еще не забронирована';
                    note.classList.toggle('game-view-location-note--reserved', data.place_reserved);
                }

                root.dataset.extraPlayers = String(data.extra_players);
                root.dataset.availableSeats = String(data.available_seats);
                if (data.team_roster) {
                    applyTeamRoster(data.team_roster);
                }
                showStatus('Изменения сохранены', false);
            } catch (e) {
                showStatus('Ошибка сети. Попробуйте ещё раз.', true);
            } finally {
                if (saveBtn) {
                    saveBtn.disabled = false;
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initMenu();
        initPlayersPanel();
        initTeamsPanel();
        initManageAction();
        initMap();
        initJoinLeave();
        initParticipationActions();
        initInvitationActions();
        initInviteModal();
        initStatusPolling();
        initShare();
        initOrganizerPanel();
    });
})();
