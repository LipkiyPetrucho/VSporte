(function () {
    const root = document.getElementById('blocked-users');
    if (!root) {
        return;
    }

    const blockUrl = root.dataset.blockUrl;

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    }

    root.addEventListener('click', function (event) {
        const button = event.target.closest('[data-unblock]');
        if (!button || !blockUrl) {
            return;
        }

        event.preventDefault();
        const userId = button.dataset.id;
        const item = button.closest('[data-blocked-user]');
        const formData = new FormData();
        formData.append('id', userId);
        formData.append('action', 'unblock');

        fetch(blockUrl, {
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
                if (item) {
                    item.remove();
                }
                const list = root.querySelector('.blocked-users__list');
                if (list && !list.querySelector('[data-blocked-user]')) {
                    list.remove();
                    const empty = document.createElement('p');
                    empty.className = 'blocked-users__empty';
                    empty.id = 'blocked-users-empty';
                    empty.textContent = 'Нет заблокированных пользователей';
                    root.appendChild(empty);
                }
            });
    });
})();
