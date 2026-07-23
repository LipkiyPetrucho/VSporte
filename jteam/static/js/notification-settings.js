(function () {
    const root = document.getElementById('notification-settings');
    if (!root) {
        return;
    }

    const updateUrl = root.dataset.updateUrl;

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    }

    root.addEventListener('change', function (event) {
        const input = event.target.closest('[data-setting-key]');
        if (!input || !updateUrl) {
            return;
        }

        const key = input.dataset.settingKey;
        const enabled = input.checked;
        input.disabled = true;

        const formData = new FormData();
        formData.append('key', key);
        formData.append('enabled', enabled ? '1' : '0');

        fetch(updateUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData,
            credentials: 'same-origin',
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.status !== 'ok') {
                    input.checked = !enabled;
                }
            })
            .catch(function () {
                input.checked = !enabled;
            })
            .finally(function () {
                input.disabled = false;
            });
    });
})();
