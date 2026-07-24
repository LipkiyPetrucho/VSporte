(function () {
    const modal = document.getElementById('deactivate-modal');
    if (!modal) {
        return;
    }

    function openModal() {
        modal.hidden = false;
        document.body.classList.add('deactivate-modal-open');
    }

    function closeModal() {
        modal.hidden = true;
        document.body.classList.remove('deactivate-modal-open');
    }

    document.querySelectorAll('[data-deactivate-open]').forEach(function (el) {
        el.addEventListener('click', openModal);
    });

    document.querySelectorAll('[data-deactivate-close]').forEach(function (el) {
        el.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !modal.hidden) {
            closeModal();
        }
    });
})();
