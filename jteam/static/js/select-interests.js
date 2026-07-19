(function () {
    const searchInput = document.getElementById('interests-search');
    const emptyState = document.getElementById('interests-empty');
    const categories = Array.from(document.querySelectorAll('[data-category]'));
    const cards = Array.from(document.querySelectorAll('[data-interest-card]'));

    function syncSelectedState(card) {
        const checkbox = card.querySelector('.select-interests__checkbox');
        if (!checkbox) {
            return;
        }
        card.classList.toggle('is-selected', checkbox.checked);
    }

    cards.forEach(function (card) {
        const checkbox = card.querySelector('.select-interests__checkbox');
        if (!checkbox) {
            return;
        }
        checkbox.addEventListener('change', function () {
            syncSelectedState(card);
        });
    });

    function filterInterests(query) {
        const normalized = (query || '').trim().toLowerCase();
        let visibleCount = 0;

        categories.forEach(function (category) {
            const categoryCards = Array.from(
                category.querySelectorAll('[data-interest-card]')
            );
            let categoryVisible = 0;

            categoryCards.forEach(function (card) {
                const label = card.dataset.interestLabel || '';
                const matches = !normalized || label.indexOf(normalized) !== -1;
                card.hidden = !matches;
                if (matches) {
                    categoryVisible += 1;
                    visibleCount += 1;
                }
            });

            category.hidden = categoryVisible === 0;
        });

        if (emptyState) {
            emptyState.hidden = visibleCount > 0;
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            filterInterests(searchInput.value);
        });
    }
})();
