(function () {
    document.querySelectorAll('[data-password-toggle]').forEach(function (button) {
        button.addEventListener('click', function () {
            const wrap = button.closest('.password-update__input-wrap');
            if (!wrap) {
                return;
            }
            const input = wrap.querySelector('input');
            if (!input) {
                return;
            }
            const icon = button.querySelector('i');
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            if (icon) {
                icon.classList.toggle('fa-eye', !show);
                icon.classList.toggle('fa-eye-slash', show);
            }
            button.setAttribute(
                'aria-label',
                show ? 'Скрыть пароль' : 'Показать пароль'
            );
        });
    });
})();
