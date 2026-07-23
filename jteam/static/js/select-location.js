(function () {
    const root = document.getElementById('select-location');
    if (!root) {
        return;
    }

    const suggestUrl = root.dataset.suggestUrl;
    const geocodeUrl = root.dataset.geocodeUrl;
    const saveUrl = root.dataset.saveUrl;
    const deleteUrl = root.dataset.deleteUrl;
    const cancelUrl = root.dataset.cancelUrl;

    const searchInput = document.getElementById('location-search');
    const clearBtn = document.getElementById('location-search-clear');
    const suggestionsSection = document.getElementById('location-suggestions-section');
    const suggestionsList = document.getElementById('location-suggestions');
    const recentSection = document.getElementById('location-recent-section');
    const recentList = document.getElementById('location-recent-list');
    const recentEmpty = document.getElementById('location-recent-empty');

    const CITY_STORAGE_KEY = 'jteam_selected_city';
    const CITY_SOURCE_KEY = 'jteam_city_source';
    const SEARCH_DEBOUNCE_MS = 250;
    const MIN_QUERY_LENGTH = 2;

    let suggestTimeout = null;
    let suggestRequestId = 0;
    let saving = false;

    function getCsrfToken() {
        if (typeof Cookies !== 'undefined') {
            return Cookies.get('csrftoken');
        }
        const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(payload),
        }).then(function (response) {
            return response.json().catch(function () {
                return {};
            }).then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || 'request_failed');
                }
                return data;
            });
        });
    }

    function syncClearButton() {
        if (!clearBtn || !searchInput) {
            return;
        }
        clearBtn.hidden = !searchInput.value.trim();
    }

    function splitLabel(label) {
        const text = (label || '').trim();
        if (!text) {
            return { title: '', address: '' };
        }
        const parts = text.split(',').map(function (part) {
            return part.trim();
        }).filter(Boolean);
        if (parts.length <= 1) {
            return { title: text, address: text };
        }
        return {
            title: parts[0],
            address: text,
        };
    }

    function hideSuggestions() {
        if (suggestionsSection) {
            suggestionsSection.hidden = true;
        }
        if (suggestionsList) {
            suggestionsList.innerHTML = '';
        }
    }

    function renderSuggestions(items) {
        if (!suggestionsList || !suggestionsSection) {
            return;
        }
        suggestionsList.innerHTML = '';
        if (!items.length) {
            hideSuggestions();
            return;
        }

        items.forEach(function (item) {
            const label = item.label || item.value || '';
            const parts = splitLabel(label);
            const li = document.createElement('li');
            li.className = 'select-location__item';

            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'select-location__item-main';

            const title = document.createElement('span');
            title.className = 'select-location__item-title';
            title.textContent = parts.title;
            button.appendChild(title);

            if (parts.address && parts.address !== parts.title) {
                const address = document.createElement('span');
                address.className = 'select-location__item-address';
                address.textContent = parts.address;
                button.appendChild(address);
            }

            button.addEventListener('click', function () {
                selectSuggestion(item, parts);
            });

            li.appendChild(button);
            suggestionsList.appendChild(li);
        });

        suggestionsSection.hidden = false;
    }

    function geocodeSuggestion(item) {
        if (!geocodeUrl) {
            return Promise.resolve({});
        }

        const params = new URLSearchParams();
        if (item.uri) {
            params.set('uri', item.uri);
        } else if (item.value || item.label) {
            params.set('q', item.value || item.label);
        } else {
            return Promise.resolve({});
        }

        return fetch(geocodeUrl + '?' + params.toString(), {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).then(function (response) {
            if (!response.ok) {
                return {};
            }
            return response.json().catch(function () {
                return {};
            });
        }).catch(function () {
            return {};
        });
    }

    function applyCityToHeader(city) {
        if (!city || !city.name) {
            return;
        }
        try {
            localStorage.setItem(CITY_STORAGE_KEY, JSON.stringify(city));
            localStorage.setItem(CITY_SOURCE_KEY, 'manual');
        } catch (error) {
            // ignore storage errors
        }
        document.querySelectorAll('[data-city-label]').forEach(function (label) {
            label.textContent = city.name;
        });
    }

    function saveLocation(payload) {
        if (saving || !saveUrl) {
            return;
        }
        saving = true;
        postJson(saveUrl, payload)
            .then(function (data) {
                if (data.city) {
                    applyCityToHeader(data.city);
                }
                window.location.href = data.redirect_url || cancelUrl || '/preferences/';
            })
            .catch(function () {
                saving = false;
                window.alert('Не удалось сохранить локацию. Попробуйте ещё раз.');
            });
    }

    function selectSuggestion(item, parts) {
        const base = {
            title: parts.title,
            address: parts.address || item.value || item.label || parts.title,
            uri: item.uri || '',
        };

        geocodeSuggestion(item).then(function (geo) {
            if (geo && geo.latitude != null && geo.longitude != null) {
                base.latitude = geo.latitude;
                base.longitude = geo.longitude;
            }
            if (geo && geo.address) {
                base.address = geo.address;
                if (!base.title) {
                    base.title = splitLabel(geo.address).title;
                }
            }
            saveLocation(base);
        });
    }

    function locationFromElement(el) {
        return {
            id: el.dataset.id || '',
            title: el.dataset.title || '',
            address: el.dataset.address || '',
            uri: el.dataset.uri || '',
            latitude: el.dataset.latitude || null,
            longitude: el.dataset.longitude || null,
        };
    }

    function updateRecentEmptyState() {
        if (!recentList || !recentSection || !recentEmpty) {
            return;
        }
        const hasItems = recentList.querySelectorAll('[data-recent-item]').length > 0;
        recentEmpty.hidden = hasItems;
        recentSection.hidden = false;
        if (!hasItems) {
            recentList.innerHTML = '';
        }
    }

    function fetchSuggestions(query) {
        if (!suggestUrl || query.length < MIN_QUERY_LENGTH) {
            hideSuggestions();
            return;
        }

        const requestId = ++suggestRequestId;
        fetch(suggestUrl + '?q=' + encodeURIComponent(query), {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('suggest_failed');
                }
                return response.json();
            })
            .then(function (data) {
                if (requestId !== suggestRequestId) {
                    return;
                }
                renderSuggestions(data.suggestions || []);
            })
            .catch(function () {
                if (requestId !== suggestRequestId) {
                    return;
                }
                hideSuggestions();
            });
    }

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            syncClearButton();
            clearTimeout(suggestTimeout);
            const query = searchInput.value.trim();
            if (query.length < MIN_QUERY_LENGTH) {
                hideSuggestions();
                return;
            }
            suggestTimeout = setTimeout(function () {
                fetchSuggestions(query);
            }, SEARCH_DEBOUNCE_MS);
        });
    }

    if (clearBtn && searchInput) {
        clearBtn.addEventListener('click', function () {
            searchInput.value = '';
            syncClearButton();
            hideSuggestions();
            searchInput.focus();
        });
    }

    if (recentList) {
        recentList.addEventListener('click', function (event) {
            const deleteBtn = event.target.closest('[data-delete-location]');
            if (deleteBtn) {
                event.preventDefault();
                const item = deleteBtn.closest('[data-recent-item]');
                if (!item || !deleteUrl) {
                    return;
                }
                const locationId = item.dataset.id;
                postJson(deleteUrl, { id: locationId })
                    .then(function () {
                        item.remove();
                        updateRecentEmptyState();
                    })
                    .catch(function () {
                        window.alert('Не удалось удалить место.');
                    });
                return;
            }

            const selectBtn = event.target.closest('[data-select-location]');
            if (selectBtn) {
                const item = selectBtn.closest('[data-recent-item]');
                if (!item) {
                    return;
                }
                saveLocation(locationFromElement(item));
            }
        });
    }

    syncClearButton();
})();
