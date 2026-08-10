(function () {
    function getCsrfToken() {
        if (typeof Cookies !== 'undefined') {
            return Cookies.get('csrftoken');
        }
        return '';
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function initMenu() {
        const menuBtn = document.getElementById('group-view-menu-btn');
        const dropdown = document.getElementById('group-view-menu-dropdown');
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

    function memberProfileUrl(member) {
        if (member.url) {
            return member.url;
        }
        return '/users/' + encodeURIComponent(member.username) + '/';
    }

    function buildMemberRow(member, currentUsername, ownerUsername, isOwner) {
        const avatar = member.photo
            ? '<img src="' + member.photo + '" alt="" class="group-view-member-avatar">'
            : '<span class="group-view-member-avatar placeholder">' +
                escapeHtml(member.username.charAt(0).toUpperCase()) +
                '</span>';

        const isCurrentUser = member.username === currentUsername;
        const isMemberOwner = member.is_owner || member.username === ownerUsername;
        const name = isCurrentUser
            ? '<span class="group-view-member-name">Вы</span>'
            : '<a href="' + memberProfileUrl(member) + '" class="group-view-member-name">' +
                escapeHtml(member.username) +
                '</a>';
        const badge = isMemberOwner
            ? '<span class="group-view-badge">Владелец</span>'
            : '';
        const removeBtn = isOwner && !isMemberOwner && member.id
            ? (
                '<button type="button" class="group-view-member-remove"' +
                ' data-action="remove_member"' +
                ' data-user-id="' + member.id + '"' +
                ' data-username="' + escapeHtml(member.username) + '"' +
                ' title="Удалить участника"' +
                ' aria-label="Удалить ' + escapeHtml(member.username) + '">' +
                '<i class="fas fa-times" aria-hidden="true"></i>' +
                '</button>'
            )
            : '';

        return (
            '<div class="group-view-member' +
            (isMemberOwner ? ' group-view-member--owner' : '') +
            '">' +
            avatar +
            '<div class="group-view-member-meta">' + name + badge + '</div>' +
            removeBtn +
            '</div>'
        );
    }

    function updateMembersCount(count) {
        const value = String(count != null ? count : 0);
        const countNode = document.getElementById('members-count');
        const titleNode = document.getElementById('members-count-title');
        if (countNode) {
            countNode.textContent = value;
        }
        if (titleNode) {
            titleNode.textContent = value;
        }
    }

    function renderMembers(members, currentUsername, ownerUsername, isOwner) {
        const preview = document.getElementById('members-preview');
        if (!preview) {
            return;
        }

        if (!members || !members.length) {
            preview.innerHTML = '<p class="group-view-empty">Пока нет участников.</p>';
            return;
        }

        preview.innerHTML = members
            .map(function (member) {
                return buildMemberRow(member, currentUsername, ownerUsername, isOwner);
            })
            .join('');
    }

    function syncMembersFromResponse(data, currentUsername, ownerUsername, isOwner) {
        if (data.members_count != null) {
            updateMembersCount(data.members_count);
        }
        if (data.members) {
            renderMembers(data.members, currentUsername, ownerUsername, isOwner);
        }
        const root = document.querySelector('.group-view');
        if (root && data.membership_status) {
            root.dataset.membershipStatus = data.membership_status;
        }
    }

    function updateJoinButton(btn, action, communityId, requestId) {
        if (!btn) {
            return;
        }

        btn.dataset.action = action;
        btn.classList.remove('group-view-action--invite', 'group-view-action--pending', 'danger');
        btn.hidden = false;
        btn.disabled = false;

        if (action === 'leave') {
            btn.dataset.id = communityId;
            btn.classList.add('danger');
            btn.removeAttribute('title');
            btn.innerHTML =
                '<span class="group-view-action-icon"><i class="fas fa-times"></i></span>Выйти';
        } else if (action === 'cancel_request') {
            btn.dataset.id = requestId || btn.dataset.id;
            btn.classList.add('group-view-action--pending');
            btn.title = 'Нажмите, чтобы отменить заявку';
            btn.innerHTML =
                '<span class="group-view-action-icon"><i class="fas fa-clock"></i></span>Заявка отправлена';
        } else if (action === 'accept_invitation') {
            btn.dataset.id = requestId || btn.dataset.id;
            btn.classList.add('group-view-action--invite');
            btn.removeAttribute('title');
            btn.innerHTML =
                '<span class="group-view-action-icon"><i class="fas fa-envelope-open"></i></span>Принять приглашение';
        } else {
            btn.dataset.id = communityId;
            btn.removeAttribute('title');
            btn.innerHTML =
                '<span class="group-view-action-icon"><i class="fas fa-plus"></i></span>Вступить';
        }
    }

    function membershipStatusToAction(status) {
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

    function postForm(url, fields) {
        const body = new FormData();
        Object.keys(fields).forEach(function (key) {
            if (fields[key] != null) {
                body.append(key, fields[key]);
            }
        });
        return fetch(url, {
            method: 'POST',
            mode: 'same-origin',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: body,
        }).then(function (response) {
            return response.json();
        });
    }

    function initJoinLeave() {
        const root = document.querySelector('.group-view');
        const joinBtn = document.getElementById('join-btn');
        if (!root || !joinBtn) {
            return;
        }

        const communityId = root.dataset.communityId;
        const ownerUsername = root.dataset.ownerUsername || '';
        const currentUsername = root.dataset.currentUsername || '';
        const isOwner = root.dataset.isOwner === '1';
        const joinUrl = root.dataset.joinUrl;
        const leaveUrl = root.dataset.leaveUrl;
        const membershipUrl = root.dataset.membershipUrl;
        const inviteUrl = root.dataset.inviteUrl;

        document.addEventListener('click', async function (event) {
            const btn = event.target.closest('#join-btn');
            if (!btn || !root.contains(btn)) {
                return;
            }

            event.preventDefault();
            const action = btn.dataset.action;
            btn.disabled = true;

            try {
                let data;

                if (action === 'accept_invitation') {
                    data = await postForm(inviteUrl, {
                        id: btn.dataset.id,
                        action: 'accept',
                    });
                } else if (action === 'cancel_request') {
                    data = await postForm(membershipUrl, {
                        id: btn.dataset.id,
                        action: 'cancel',
                    });
                } else if (action === 'leave') {
                    data = await postForm(leaveUrl, { id: communityId });
                } else {
                    data = await postForm(joinUrl, { id: communityId });
                }

                if (data.status !== 'ok') {
                    alert(data.message || 'Не удалось обновить участие');
                    btn.disabled = false;
                    return;
                }

                syncMembersFromResponse(data, currentUsername, ownerUsername, isOwner);

                if (action === 'cancel_request') {
                    updateJoinButton(btn, 'join', communityId);
                    const declineBtn = document.getElementById('decline-invite-btn');
                    if (declineBtn) {
                        declineBtn.remove();
                    }
                    return;
                }

                const nextAction = data.membership_status
                    ? membershipStatusToAction(data.membership_status)
                    : (action === 'join' ? 'cancel_request' : 'join');
                const actionId = data.join_request_id
                    || data.invitation_id
                    || btn.dataset.id;

                if (nextAction === 'leave' && isOwner) {
                    btn.disabled = true;
                    btn.classList.remove('danger', 'group-view-action--invite', 'group-view-action--pending');
                    btn.innerHTML =
                        '<span class="group-view-action-icon"><i class="fas fa-crown"></i></span>Владелец';
                    btn.removeAttribute('data-action');
                } else {
                    updateJoinButton(btn, nextAction, communityId, actionId);
                }

                const declineBtn = document.getElementById('decline-invite-btn');
                if (declineBtn && nextAction !== 'accept_invitation') {
                    declineBtn.remove();
                }
            } catch (e) {
                alert('Ошибка сети. Попробуйте ещё раз.');
                btn.disabled = false;
            }
        });
    }

    function initRemoveMember() {
        const root = document.querySelector('.group-view');
        if (!root || root.dataset.isOwner !== '1') {
            return;
        }

        const membershipUrl = root.dataset.membershipUrl;
        const communityId = root.dataset.communityId;
        const ownerUsername = root.dataset.ownerUsername || '';
        const currentUsername = root.dataset.currentUsername || '';

        document.addEventListener('click', async function (event) {
            const btn = event.target.closest('[data-action="remove_member"]');
            if (!btn || !root.contains(btn)) {
                return;
            }

            event.preventDefault();
            const username = btn.dataset.username || 'участника';
            if (!window.confirm('Удалить ' + username + ' из группы?')) {
                return;
            }

            btn.disabled = true;
            try {
                const data = await postForm(membershipUrl, {
                    action: 'remove_member',
                    community_id: communityId,
                    user_id: btn.dataset.userId,
                });
                if (data.status !== 'ok') {
                    alert(data.message || 'Не удалось удалить участника');
                    btn.disabled = false;
                    return;
                }
                syncMembersFromResponse(data, currentUsername, ownerUsername, true);
            } catch (e) {
                alert('Ошибка сети. Попробуйте ещё раз.');
                btn.disabled = false;
            }
        });
    }

    function appendPendingInvitation(invitationId, username, avatarHtml, profileUrl) {
        let block = document.getElementById('pending-invitations-block');
        if (!block) {
            const anchor = document.getElementById('join-requests-block')
                || document.querySelector('.group-view-actions');
            if (!anchor) {
                return;
            }
            anchor.insertAdjacentHTML(
                'afterend',
                '<div class="group-view-requests group-view-invitations" id="pending-invitations-block">' +
                    '<h3 class="group-view-card-title">Отправленные приглашения</h3>' +
                    '<ul class="group-view-requests-list" id="pending-invitations-list"></ul>' +
                '</div>'
            );
            block = document.getElementById('pending-invitations-block');
        }

        const list = document.getElementById('pending-invitations-list');
        if (!list) {
            return;
        }

        list.insertAdjacentHTML(
            'beforeend',
            '<li class="group-view-request">' +
                '<div class="group-view-request-user">' +
                    avatarHtml +
                    '<a href="' + profileUrl + '" class="group-view-member-name">' +
                        escapeHtml(username) +
                    '</a>' +
                '</div>' +
                '<div class="group-view-request-actions">' +
                    '<button type="button" class="group-view-request-btn reject" ' +
                        'data-invitation-id="' + invitationId + '" data-action="cancel">Отменить</button>' +
                '</div>' +
            '</li>'
        );
    }

    function initMembershipActions() {
        const root = document.querySelector('.group-view');
        if (!root) {
            return;
        }

        const membershipUrl = root.dataset.membershipUrl;
        if (!membershipUrl) {
            return;
        }

        const ownerUsername = root.dataset.ownerUsername || '';
        const currentUsername = root.dataset.currentUsername || '';
        const isOwner = root.dataset.isOwner === '1';

        document.addEventListener('click', async function (event) {
            const btn = event.target.closest('[data-join-request-id]');
            if (!btn || !root.contains(btn)) {
                return;
            }

            event.preventDefault();
            btn.disabled = true;

            try {
                const data = await postForm(membershipUrl, {
                    id: btn.dataset.joinRequestId,
                    action: btn.dataset.action,
                });
                if (data.status !== 'ok') {
                    alert(data.message || 'Не удалось обработать заявку');
                    btn.disabled = false;
                    return;
                }

                const requestItem = btn.closest('.group-view-request');
                if (requestItem) {
                    requestItem.remove();
                }

                const requestsList = document.getElementById('join-requests-list');
                if (requestsList && !requestsList.children.length) {
                    const requestsBlock = document.getElementById('join-requests-block');
                    if (requestsBlock) {
                        requestsBlock.remove();
                    }
                }

                if (data.members) {
                    syncMembersFromResponse(data, currentUsername, ownerUsername, isOwner);
                }
            } catch (e) {
                alert('Ошибка сети. Попробуйте ещё раз.');
                btn.disabled = false;
            }
        });
    }

    function initInvitationActions() {
        const root = document.querySelector('.group-view');
        if (!root) {
            return;
        }

        const inviteUrl = root.dataset.inviteUrl;
        if (!inviteUrl) {
            return;
        }

        const communityId = root.dataset.communityId;

        document.addEventListener('click', async function (event) {
            const declineBtn = event.target.closest('#decline-invite-btn');
            if (declineBtn && root.contains(declineBtn)) {
                event.preventDefault();
                declineBtn.disabled = true;
                try {
                    const data = await postForm(inviteUrl, {
                        id: declineBtn.dataset.id,
                        action: 'decline',
                    });
                    if (data.status !== 'ok') {
                        alert(data.message || 'Не удалось отклонить приглашение');
                        declineBtn.disabled = false;
                        return;
                    }
                    declineBtn.remove();
                    const joinBtn = document.getElementById('join-btn');
                    if (joinBtn) {
                        updateJoinButton(joinBtn, 'join', communityId);
                    }
                } catch (e) {
                    alert('Ошибка сети. Попробуйте ещё раз.');
                    declineBtn.disabled = false;
                }
                return;
            }

            const cancelBtn = event.target.closest('[data-invitation-id][data-action="cancel"]');
            if (!cancelBtn || !root.contains(cancelBtn)) {
                return;
            }

            event.preventDefault();
            cancelBtn.disabled = true;
            try {
                const data = await postForm(inviteUrl, {
                    id: cancelBtn.dataset.invitationId,
                    action: 'cancel',
                });
                if (data.status !== 'ok') {
                    alert(data.message || 'Не удалось отменить приглашение');
                    cancelBtn.disabled = false;
                    return;
                }

                const invitationItem = cancelBtn.closest('.group-view-request');
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
            } catch (e) {
                alert('Ошибка сети. Попробуйте ещё раз.');
                cancelBtn.disabled = false;
            }
        });
    }

    function initInviteModal() {
        const root = document.querySelector('.group-view');
        const addBtn = document.getElementById('group-action-invite');
        const modal = document.getElementById('group-invite-modal');
        if (!root || !addBtn || !modal) {
            return;
        }

        const inviteUrl = root.dataset.inviteUrl;
        const communityId = root.dataset.communityId;
        const closeBtn = document.getElementById('group-invite-close');
        const backdrop = document.getElementById('group-invite-backdrop');

        function openModal() {
            modal.hidden = false;
            document.body.classList.add('group-invite-modal-open');
        }

        function closeModal() {
            modal.hidden = true;
            document.body.classList.remove('group-invite-modal-open');
        }

        addBtn.addEventListener('click', openModal);
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

            try {
                const data = await postForm(inviteUrl, {
                    action: 'invite',
                    community_id: communityId,
                    to_user_id: inviteBtn.dataset.userId,
                });
                if (data.status !== 'ok') {
                    alert(data.message || 'Не удалось отправить приглашение');
                    inviteBtn.disabled = false;
                    return;
                }

                const inviteItem = inviteBtn.closest('.group-view-invite-item');
                if (inviteItem) {
                    const usernameNode = inviteItem.querySelector('.group-view-member-name');
                    const avatarNode = inviteItem.querySelector('.group-view-member-avatar');
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

                const inviteList = document.getElementById('group-invite-list');
                if (inviteList && !inviteList.children.length) {
                    const emptyNode = document.getElementById('group-invite-empty');
                    if (!emptyNode) {
                        const dialog = modal.querySelector('.group-view-invite-dialog');
                        if (dialog) {
                            dialog.insertAdjacentHTML(
                                'beforeend',
                                '<p class="group-view-empty" id="group-invite-empty">Нет друзей для приглашения</p>'
                            );
                        }
                    }
                }

                closeModal();
            } catch (e) {
                alert('Ошибка сети. Попробуйте ещё раз.');
                inviteBtn.disabled = false;
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (!document.querySelector('.group-view')) {
            return;
        }
        initMenu();
        initJoinLeave();
        initRemoveMember();
        initMembershipActions();
        initInvitationActions();
        initInviteModal();
    });
})();
