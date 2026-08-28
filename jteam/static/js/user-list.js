(function () {
    const friendshipUrl = document.body.dataset.friendshipUrl;
    const usersPage = document.querySelector('.users-page');
    if (!friendshipUrl || !usersPage) {
        return;
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    }

    function renderAction(container, userId, friendship) {
        if (friendship === 'pending_sent') {
            container.innerHTML =
                '<span class="users-page__pending">' +
                'В ожидании <i class="far fa-hourglass" aria-hidden="true"></i>' +
                '</span>';
            return;
        }

        if (friendship === 'friends') {
            container.innerHTML =
                '<button type="button" class="users-page__friend-btn users-page__friend-btn--remove" ' +
                'data-id="' + userId + '" data-action="unfriend" aria-label="Удалить из друзей">' +
                '<i class="fas fa-user-minus" aria-hidden="true"></i></button>';
            return;
        }

        const action = friendship === 'pending_received' ? 'accept' : 'request';
        const label = friendship === 'pending_received' ? 'Принять заявку' : 'Добавить в друзья';
        container.innerHTML =
            '<button type="button" class="users-page__friend-btn users-page__friend-btn--add" ' +
            'data-id="' + userId + '" data-action="' + action + '" aria-label="' + label + '">' +
            '<i class="fas fa-user-plus" aria-hidden="true"></i></button>';
    }

    function updateRequestBadge(tabName) {
        const tab = document.querySelector(
            '.users-page__requests-tab[href*="requests=' + tabName + '"]'
        );
        if (!tab) {
            return;
        }
        const list = document.getElementById('users-requests-list');
        const count = list ? list.querySelectorAll('.users-page__card').length : 0;
        let badge = tab.querySelector('.users-page__requests-badge');
        if (count > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'users-page__requests-badge';
                tab.appendChild(badge);
            }
            badge.textContent = String(count);
        } else if (badge) {
            badge.remove();
        }
    }

    function showRequestsEmptyState(list) {
        if (!list || list.querySelector('.users-page__card')) {
            return;
        }
        const isIncoming = window.location.search.indexOf('requests=outgoing') === -1;
        const empty = document.createElement('p');
        empty.className = 'users-page__empty users-page__empty--requests';
        empty.textContent = isIncoming
            ? 'Входящих заявок пока нет.'
            : 'Исходящих заявок пока нет.';
        list.appendChild(empty);
    }

    usersPage.addEventListener('click', function (event) {
        const button = event.target.closest('.users-page__friend-btn');
        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const card = button.closest('.users-page__card');
        const actionContainer = card.querySelector('[data-friendship-action]');
        const requestsList = document.getElementById('users-requests-list');
        const isRequestList = requestsList && requestsList.contains(card);
        const formData = new FormData();
        formData.append('id', button.dataset.id);
        formData.append('action', button.dataset.action);

        fetch(friendshipUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData,
            credentials: 'same-origin',
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.status !== 'ok') {
                    return;
                }

                if (isRequestList) {
                    card.remove();
                    const emptyState = requestsList.querySelector('.users-page__empty--requests');
                    if (emptyState) {
                        emptyState.remove();
                    }
                    updateRequestBadge('incoming');
                    updateRequestBadge('outgoing');
                    showRequestsEmptyState(requestsList);
                    return;
                }

                renderAction(actionContainer, button.dataset.id, data.friendship);
            });
    });

    const searchToggle = document.getElementById('users-search-toggle');
    const searchPanel = document.getElementById('users-page-search');
    if (searchToggle && searchPanel) {
        searchToggle.addEventListener('click', function () {
            const isOpen = searchPanel.classList.toggle('is-open');
            searchToggle.setAttribute('aria-expanded', String(isOpen));
            if (isOpen) {
                const input = searchPanel.querySelector('input');
                if (input) {
                    input.focus();
                }
            }
        });
    }

    const filterToggle = document.getElementById('users-filter-toggle');
    const filterPanel = document.getElementById('users-page-filter');
    if (filterToggle && filterPanel) {
        filterToggle.addEventListener('click', function () {
            const isOpen = filterPanel.classList.toggle('is-open');
            filterToggle.setAttribute('aria-expanded', String(isOpen));
        });
    }

    var page = 1;
    var emptyPage = false;
    var blockRequest = false;
    var moreBtn = document.getElementById('users-page-more-btn');
    var moreWrap = moreBtn ? moreBtn.closest('.users-page-more') : null;

    function hideMoreButton() {
        if (moreWrap) {
            moreWrap.hidden = true;
        }
    }

    function loadMoreUsers() {
        if (emptyPage || blockRequest) {
            return;
        }
        blockRequest = true;
        if (moreBtn) {
            moreBtn.disabled = true;
        }
        page += 1;

        var urlParams = new URLSearchParams(window.location.search);
        urlParams.set('page', page);
        urlParams.set('users_only', '1');

        fetch('?' + urlParams.toString(), { credentials: 'same-origin' })
            .then(function (response) {
                var hasNext = response.headers.get('X-Has-Next');
                return response.text().then(function (html) {
                    return { html: html, hasNext: hasNext };
                });
            })
            .then(function (result) {
                var html = result.html;
                if (!html || !html.trim()) {
                    emptyPage = true;
                    hideMoreButton();
                    return;
                }
                var usersList = document.getElementById('users-list');
                if (usersList) {
                    usersList.insertAdjacentHTML('beforeend', html);
                }
                if (result.hasNext === '0') {
                    emptyPage = true;
                    hideMoreButton();
                    return;
                }
                blockRequest = false;
                if (moreBtn) {
                    moreBtn.disabled = false;
                }
            })
            .catch(function () {
                blockRequest = false;
                page -= 1;
                if (moreBtn) {
                    moreBtn.disabled = false;
                }
            });
    }

    if (moreBtn) {
        moreBtn.addEventListener('click', loadMoreUsers);
    }
})();
