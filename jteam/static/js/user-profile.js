(function () {
    const friendshipUrl = document.body.dataset.friendshipUrl;
    const blockUrl = document.body.dataset.blockUrl;
    const actionContainer = document.querySelector('[data-friendship-action]');
    const menuRoot = document.querySelector('[data-profile-menu]');

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    }

    function renderAction(userId, friendship) {
        if (!actionContainer) {
            return;
        }

        if (friendship === 'pending_sent') {
            actionContainer.innerHTML =
                '<span class="profile-page__pending">Заявка отправлена</span>';
            return;
        }

        if (friendship === 'friends') {
            actionContainer.innerHTML =
                '<button type="button" class="profile-page__friend-btn profile-page__friend-btn--remove" ' +
                'data-id="' + userId + '" data-action="unfriend">Удалить из друзей</button>';
            return;
        }

        const action = friendship === 'pending_received' ? 'accept' : 'request';
        const label = friendship === 'pending_received' ? 'Принять заявку' : 'Добавить в друзья';
        actionContainer.innerHTML =
            '<button type="button" class="profile-page__friend-btn" ' +
            'data-id="' + userId + '" data-action="' + action + '">' + label + '</button>';
    }

    if (actionContainer && friendshipUrl) {
        actionContainer.addEventListener('click', function (event) {
            const button = event.target.closest('.profile-page__friend-btn');
            if (!button) {
                return;
            }

            event.preventDefault();

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
                    if (data.status === 'ok') {
                        renderAction(button.dataset.id, data.friendship);
                    }
                });
        });
    }

    if (menuRoot) {
        const toggle = menuRoot.querySelector('[data-profile-menu-toggle]');
        const dropdown = menuRoot.querySelector('.profile-page__menu-dropdown');

        function closeMenu() {
            if (!dropdown || !toggle) {
                return;
            }
            dropdown.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
        }

        function openMenu() {
            if (!dropdown || !toggle) {
                return;
            }
            dropdown.hidden = false;
            toggle.setAttribute('aria-expanded', 'true');
        }

        if (toggle && dropdown) {
            toggle.addEventListener('click', function (event) {
                event.stopPropagation();
                if (dropdown.hidden) {
                    openMenu();
                } else {
                    closeMenu();
                }
            });

            document.addEventListener('click', function (event) {
                if (!menuRoot.contains(event.target)) {
                    closeMenu();
                }
            });
        }

        menuRoot.addEventListener('click', function (event) {
            const blockBtn = event.target.closest('[data-block-action]');
            if (!blockBtn || !blockUrl) {
                return;
            }

            event.preventDefault();
            const action = blockBtn.dataset.blockAction;
            const userId = blockBtn.dataset.id;
            const confirmText = action === 'block'
                ? 'Заблокировать этого пользователя?'
                : 'Разблокировать этого пользователя?';

            if (!window.confirm(confirmText)) {
                closeMenu();
                return;
            }

            const formData = new FormData();
            formData.append('id', userId);
            formData.append('action', action);

            fetch(blockUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: formData,
                credentials: 'same-origin',
            })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (data.status === 'ok') {
                        window.location.reload();
                    }
                });
        });
    }
})();
