document.addEventListener('DOMContentLoaded', function () {
    var root = document.querySelector('[data-create-game]');
    if (!root) {
        return;
    }

    var isEditMode = root.dataset.editMode === '1';
    var minPlayers = Number(root.dataset.minPlayers) || 2;

    var form = document.getElementById('create-game-form');
    var steps = Array.prototype.slice.call(root.querySelectorAll('[data-step]'));
    var tabs = Array.prototype.slice.call(root.querySelectorAll('[data-tab]'));
    var nextBtn = root.querySelector('[data-action="next"]');
    var backBtn = root.querySelector('[data-action="back"]');
    var submitBtn = root.querySelector('[data-action="submit"]');
    var currentStep = 1;
    var maxStep = steps.length;

    var sportSelect = document.getElementById('id_sport');
    var sportLabel = root.querySelector('[data-sport-label]');
    var sportTrigger = root.querySelector('[data-sport-trigger]');
    var sportSheet = document.getElementById('create-event-sport-sheet');
    var sportItems = root.querySelectorAll('[data-sport-value]');

    var skillToggle = root.querySelector('[data-skill-toggle]');
    var skillPanel = root.querySelector('[data-skill-panel]');
    var skillLabel = root.querySelector('[data-skill-label]');
    var skillSelect = document.getElementById('id_skill_level');
    var skillSheet = document.getElementById('create-event-skill-sheet');
    var skillItems = root.querySelectorAll('[data-skill-value]');
    var skillSlider = root.querySelector('[data-skill-slider]');
    var skillFill = root.querySelector('[data-skill-fill]');
    var skillThumb = root.querySelector('[data-skill-thumb]');
    var skillDots = root.querySelectorAll('[data-skill-dot]');
    var skillLevels = [
        { value: 'beginner', label: 'Начинающий' },
        { value: 'intermediate', label: 'Средний' },
        { value: 'advanced', label: 'Продвинутый' },
        { value: 'pro', label: 'Профи' }
    ];
    var skillIndex = 0;
    var placeInput = document.getElementById('id_place');
    var venueInput = document.getElementById('create-event-venue-input');
    var venueLabel = root.querySelector('[data-venue-label]');
    var venueTrigger = root.querySelector('[data-venue-trigger]');
    var venueSheet = document.getElementById('create-event-venue-sheet');
    var venueConfirm = root.querySelector('[data-venue-confirm]');
    var maxPlayersInput = document.getElementById('id_max_players');
    var startTimeInput = document.getElementById('id_start_time');
    var durationInput = document.getElementById('id_duration');
    var priceInput = document.getElementById('id_price');
    var dateTrigger = root.querySelector('[data-date-trigger]');
    var timeTrigger = root.querySelector('[data-time-trigger]');
    var dateLabel = root.querySelector('[data-date-label]');
    var timeLabel = root.querySelector('[data-time-label]');
    var dateSheet = document.getElementById('create-event-date-sheet');
    var datePreview = root.querySelector('[data-date-preview]');
    var dateGrid = root.querySelector('[data-date-grid]');
    var dateYearSelect = root.querySelector('[data-date-year]');
    var dateConfirm = root.querySelector('[data-date-confirm]');
    var datePrevMonth = root.querySelector('[data-date-prev-month]');
    var dateNextMonth = root.querySelector('[data-date-next-month]');
    var timeSheet = document.getElementById('create-event-time-sheet');
    var timeConfirm = root.querySelector('[data-time-confirm]');
    var timeHourDisplay = root.querySelector('[data-time-hour-display]');
    var timeMinuteDisplay = root.querySelector('[data-time-minute-display]');
    var timeHand = root.querySelector('[data-time-hand]');
    var timeLabels = root.querySelector('[data-time-labels]');
    var durationLabel = root.querySelector('[data-duration-label]');
    var durationButtons = root.querySelectorAll('[data-duration-hours]');
    var pricePerPlayer = root.querySelector('[data-price-per-player]');
    var selectedDate = null;
    var selectedTime = null;
    var pickerDate = null;
    var pickerHour = 0;
    var pickerMinute = 0;
    var timePickerMode = 'hour';
    var viewYear = null;
    var viewMonth = null;

    function parseISODate(iso) {
        var parts = iso.split('-');
        return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    }

    function toISODate(date) {
        var year = date.getFullYear();
        var month = String(date.getMonth() + 1).padStart(2, '0');
        var day = String(date.getDate()).padStart(2, '0');
        return year + '-' + month + '-' + day;
    }

    function todayISO() {
        return toISODate(new Date());
    }

    function isPastDate(iso) {
        return iso < todayISO();
    }

    function isToday(iso) {
        return iso === todayISO();
    }

    function buildLocalDateTime(iso, time) {
        var dateParts = iso.split('-');
        var timeParts = time.split(':');
        return new Date(
            Number(dateParts[0]),
            Number(dateParts[1]) - 1,
            Number(dateParts[2]),
            Number(timeParts[0]),
            Number(timeParts[1]),
            0,
            0
        );
    }

    function isPastDateTime(iso, time) {
        if (!iso || !time) {
            return false;
        }
        var selected = buildLocalDateTime(iso, time);
        var now = new Date();
        now.setSeconds(0, 0);
        return selected <= now;
    }

    function isHourInPast(hour, iso) {
        var dateIso = iso || selectedDate;
        if (!dateIso || !isToday(dateIso)) {
            return false;
        }
        return hour < new Date().getHours();
    }

    function isMinuteInPast(hour, minute, iso) {
        var dateIso = iso || selectedDate;
        if (!dateIso || !isToday(dateIso)) {
            return false;
        }
        var now = new Date();
        if (hour > now.getHours()) {
            return false;
        }
        if (hour < now.getHours()) {
            return true;
        }
        return minute <= now.getMinutes();
    }

    function getDefaultPickerTimeForDate(iso) {
        if (!iso || !isToday(iso)) {
            return { hour: 12, minute: 0 };
        }
        var now = new Date();
        var hour = now.getHours();
        var minute = Math.ceil((now.getMinutes() + 1) / 5) * 5;
        if (minute >= 60) {
            hour += 1;
            minute = 0;
        }
        if (hour >= 24) {
            hour = 23;
            minute = 55;
        }
        return { hour: hour, minute: minute };
    }

    function isMonthInPast(year, month) {
        var now = new Date();
        return year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth());
    }

    function formatDateForLabel(iso) {
        return parseISODate(iso).toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
        });
    }

    function formatDatePreview(iso) {
        return parseISODate(iso).toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
        }) + ' г.';
    }

    function syncSportLabel() {
        if (!sportSelect || !sportLabel) {
            return;
        }
        var option = sportSelect.options[sportSelect.selectedIndex];
        if (option && option.value) {
            sportLabel.textContent = option.textContent;
            sportLabel.classList.add('create-event__row-value--filled');
        } else {
            sportLabel.textContent = 'Выберите';
            sportLabel.classList.remove('create-event__row-value--filled');
        }

        sportItems.forEach(function (item) {
            item.classList.toggle('is-selected', item.dataset.sportValue === sportSelect.value);
        });
    }

    function syncVenueLabel() {
        if (!venueLabel) {
            return;
        }
        var value = placeInput ? placeInput.value.trim() : '';
        if (value) {
            venueLabel.textContent = value;
            venueLabel.classList.add('create-event__row-value--filled');
        } else {
            venueLabel.textContent = 'Выберите';
            venueLabel.classList.remove('create-event__row-value--filled');
        }
    }

    function padTimePart(value) {
        return String(value).padStart(2, '0');
    }

    function formatPickerTime() {
        return padTimePart(pickerHour) + ':' + padTimePart(pickerMinute);
    }

    function valueToClockAngle(value, stepCount) {
        return (value * (360 / stepCount)) - 90;
    }

    function placeClockLabel(container, label, xPercent, yPercent, options) {
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'create-event__clock-label';
        button.textContent = label;
        button.style.left = xPercent + '%';
        button.style.top = yPercent + '%';

        if (options && options.inner) {
            button.classList.add('create-event__clock-label--inner');
        }
        if (options && options.selected) {
            button.classList.add('create-event__clock-label--selected');
        }
        if (options && options.disabled) {
            button.disabled = true;
            button.classList.add('create-event__clock-label--disabled');
            container.appendChild(button);
            return button;
        }

        button.addEventListener('click', options.onSelect);
        container.appendChild(button);
        return button;
    }

    function polarToPercent(angleDeg, radiusPercent) {
        var radians = angleDeg * Math.PI / 180;
        return {
            x: 50 + Math.sin(radians) * radiusPercent,
            y: 50 - Math.cos(radians) * radiusPercent,
        };
    }

    function updateTimeDigitalDisplay() {
        if (timeHourDisplay) {
            timeHourDisplay.textContent = padTimePart(pickerHour);
            timeHourDisplay.classList.toggle('create-event__time-digit--active', timePickerMode === 'hour');
        }
        if (timeMinuteDisplay) {
            timeMinuteDisplay.textContent = padTimePart(pickerMinute);
            timeMinuteDisplay.classList.toggle('create-event__time-digit--active', timePickerMode === 'minute');
        }
    }

    function updateTimeHand(lengthPercent) {
        if (!timeHand) {
            return;
        }
        var value = timePickerMode === 'hour' ? pickerHour : pickerMinute;
        var stepCount = timePickerMode === 'hour' ? 12 : 60;
        var angle = valueToClockAngle(timePickerMode === 'hour' ? (value % 12) : value, stepCount);
        timeHand.style.transform = 'rotate(' + angle + 'deg)';

        var line = timeHand.querySelector('.create-event__clock-hand-line');
        var knob = timeHand.querySelector('.create-event__clock-hand-knob');
        if (line) {
            var faceSize = timeHand.parentElement ? timeHand.parentElement.clientWidth : 300;
            var handLength = faceSize * (lengthPercent / 100);
            line.style.height = handLength + 'px';
            if (knob) {
                knob.style.top = (-handLength - 14) + 'px';
            }
        }
    }

    function renderHourClock() {
        if (!timeLabels) {
            return;
        }

        timeLabels.innerHTML = '';
        var radiusOuter = 38;
        var radiusInner = 24;

        for (var hour = 1; hour <= 12; hour += 1) {
            var outerPos = polarToPercent(valueToClockAngle(hour % 12, 12), radiusOuter);
            placeClockLabel(timeLabels, String(hour), outerPos.x, outerPos.y, {
                selected: pickerHour === hour,
                disabled: isHourInPast(hour),
                onSelect: function (event) {
                    pickerHour = Number(event.currentTarget.textContent);
                    timePickerMode = 'minute';
                    renderTimePicker();
                },
            });
        }

        for (var innerHour = 13; innerHour <= 23; innerHour += 1) {
            var innerPos = polarToPercent(valueToClockAngle(innerHour % 12, 12), radiusInner);
            placeClockLabel(timeLabels, String(innerHour), innerPos.x, innerPos.y, {
                inner: true,
                selected: pickerHour === innerHour,
                disabled: isHourInPast(innerHour),
                onSelect: function (event) {
                    pickerHour = Number(event.currentTarget.textContent);
                    timePickerMode = 'minute';
                    renderTimePicker();
                },
            });
        }

        var zeroPos = polarToPercent(valueToClockAngle(0, 12), radiusInner);
        placeClockLabel(timeLabels, '0', zeroPos.x, zeroPos.y, {
            inner: true,
            selected: pickerHour === 0,
            disabled: isHourInPast(0),
            onSelect: function () {
                pickerHour = 0;
                timePickerMode = 'minute';
                renderTimePicker();
            },
        });

        updateTimeHand(pickerHour >= 13 || pickerHour === 0 ? radiusInner : radiusOuter);
    }

    function renderMinuteClock() {
        if (!timeLabels) {
            return;
        }

        timeLabels.innerHTML = '';
        var radius = 38;

        for (var minute = 0; minute < 60; minute += 5) {
            var label = padTimePart(minute);
            var pos = polarToPercent(valueToClockAngle(minute, 60), radius);
            placeClockLabel(timeLabels, label, pos.x, pos.y, {
                selected: pickerMinute === minute,
                disabled: isMinuteInPast(pickerHour, minute),
                onSelect: function (event) {
                    pickerMinute = Number(event.currentTarget.textContent);
                    renderTimePicker();
                },
            });
        }

        updateTimeHand(radius);
    }

    function renderTimePicker() {
        updateTimeDigitalDisplay();
        if (timePickerMode === 'hour') {
            renderHourClock();
        } else {
            renderMinuteClock();
        }
    }

    function openTimeSheet() {
        if (selectedTime) {
            var timeParts = selectedTime.split(':');
            pickerHour = Number(timeParts[0]) || 0;
            pickerMinute = Number(timeParts[1]) || 0;
        } else {
            var defaults = getDefaultPickerTimeForDate(selectedDate);
            pickerHour = defaults.hour;
            pickerMinute = defaults.minute;
        }
        if (selectedDate && isPastDateTime(selectedDate, formatPickerTime())) {
            var corrected = getDefaultPickerTimeForDate(selectedDate);
            pickerHour = corrected.hour;
            pickerMinute = corrected.minute;
        }
        timePickerMode = 'hour';
        renderTimePicker();
        openSheet(timeSheet);
        window.requestAnimationFrame(function () {
            renderTimePicker();
        });
    }

    function formatTimeForLabel(time, durationHours) {
        var parts = time.split(':');
        if (parts.length !== 2) {
            return '';
        }
        var startHour = Number(parts[0]);
        var startMinute = Number(parts[1]);
        var startMinutesTotal = startHour * 60 + startMinute;
        var endMinutesTotal = startMinutesTotal + Math.round(durationHours * 60);
        var endHour = Math.floor(endMinutesTotal / 60) % 24;
        var endMinute = endMinutesTotal % 60;

        var start = String(startHour).padStart(2, '0') + ':' + String(startMinute).padStart(2, '0');
        var end = String(endHour).padStart(2, '0') + ':' + String(endMinute).padStart(2, '0');
        return start + ' - ' + end;
    }

    function getDurationHours() {
        if (!durationInput || !durationInput.value) {
            return 1;
        }
        return Number(durationInput.value);
    }

    function setDurationHours(hours) {
        if (!durationInput) {
            return;
        }
        var numericHours = Number(hours);
        var matched = false;

        for (var i = 0; i < durationInput.options.length; i += 1) {
            var option = durationInput.options[i];
            if (Number(option.value) === numericHours) {
                durationInput.value = option.value;
                matched = true;
                break;
            }
        }

        if (!matched) {
            durationInput.value = String(hours);
        }

        syncDurationButtons();
    }

    function syncDurationButtons() {
        var current = getDurationHours();
        durationButtons.forEach(function (button) {
            button.classList.toggle(
                'create-event__duration-btn--active',
                Number(button.dataset.durationHours) === current
            );
        });
    }

    function updateStartTimeValue() {
        if (!startTimeInput || !selectedDate || !selectedTime) {
            return;
        }
        var dateParts = selectedDate.split('-');
        var timeParts = selectedTime.split(':');
        if (dateParts.length !== 3 || timeParts.length !== 2) {
            return;
        }
        startTimeInput.value = [
            dateParts[2],
            dateParts[1],
            dateParts[0]
        ].join('.') + ' ' + selectedTime;
    }

    function updateDateTimeLabels() {
        if (dateLabel) {
            if (selectedDate) {
                dateLabel.textContent = formatDateForLabel(selectedDate);
            } else {
                dateLabel.textContent = 'Не выбрано';
            }
        }

        if (timeLabel) {
            if (selectedTime) {
                timeLabel.textContent = formatTimeForLabel(selectedTime, getDurationHours());
            } else {
                timeLabel.textContent = 'Не выбрано';
            }
        }
    }

    function updateDurationLabel() {
        var minutes = Math.round(getDurationHours() * 60);
        if (durationLabel) {
            durationLabel.textContent = minutes + ' мин';
        }
        updateDateTimeLabels();
    }

    function updatePricePerPlayer() {
        if (!pricePerPlayer) {
            return;
        }
        var players = maxPlayersInput ? Number(maxPlayersInput.value || 0) : 0;
        var totalPrice = priceInput ? Number(priceInput.value || 0) : 0;
        if (!players || players < 1) {
            pricePerPlayer.textContent = '0';
            return;
        }
        pricePerPlayer.textContent = String(Math.round(totalPrice / players));
    }

    function anySheetOpen() {
        return root.querySelectorAll('.create-event__sheet:not([hidden])').length > 0;
    }

    function openSheet(sheet) {
        if (!sheet) {
            return;
        }
        sheet.hidden = false;
        document.body.style.overflow = 'hidden';
    }

    function closeSheet(sheet) {
        if (!sheet) {
            return;
        }
        sheet.hidden = true;
        if (!anySheetOpen()) {
            document.body.style.overflow = '';
        }
    }

    function closeAllSheets() {
        root.querySelectorAll('.create-event__sheet').forEach(function (sheet) {
            sheet.hidden = true;
        });
        document.body.style.overflow = '';
    }

    function populateYearSelect() {
        if (!dateYearSelect) {
            return;
        }
        var currentYear = new Date().getFullYear();
        dateYearSelect.innerHTML = '';
        for (var year = currentYear; year <= currentYear + 5; year += 1) {
            var option = document.createElement('option');
            option.value = String(year);
            option.textContent = String(year);
            dateYearSelect.appendChild(option);
        }
    }

    function syncDatePickerPreview() {
        if (datePreview && pickerDate) {
            datePreview.textContent = formatDatePreview(pickerDate);
        }
    }

    function renderDateCalendar() {
        if (!dateGrid || viewYear === null || viewMonth === null) {
            return;
        }

        if (dateYearSelect) {
            dateYearSelect.value = String(viewYear);
        }

        dateGrid.innerHTML = '';
        var firstDay = new Date(viewYear, viewMonth, 1);
        var daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
        var startOffset = (firstDay.getDay() + 6) % 7;
        var today = todayISO();

        for (var i = 0; i < startOffset; i += 1) {
            var emptyCell = document.createElement('span');
            emptyCell.className = 'create-event__calendar-day create-event__calendar-day--empty';
            dateGrid.appendChild(emptyCell);
        }

        for (var day = 1; day <= daysInMonth; day += 1) {
            var iso = toISODate(new Date(viewYear, viewMonth, day));
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'create-event__calendar-day';
            button.textContent = String(day);
            button.setAttribute('role', 'gridcell');

            if (iso === today) {
                button.classList.add('create-event__calendar-day--today');
            }
            if (pickerDate === iso) {
                button.classList.add('create-event__calendar-day--selected');
            }
            if (isPastDate(iso)) {
                button.disabled = true;
                button.classList.add('create-event__calendar-day--muted');
            }

            button.addEventListener('click', function (event) {
                var chosen = event.currentTarget.dataset.iso;
                if (!chosen || isPastDate(chosen)) {
                    return;
                }
                pickerDate = chosen;
                syncDatePickerPreview();
                renderDateCalendar();
            });

            button.dataset.iso = iso;
            dateGrid.appendChild(button);
        }

        syncDatePickerPreview();
    }

    function openDateSheet() {
        var baseDate = selectedDate ? parseISODate(selectedDate) : new Date();
        if (!selectedDate && isPastDate(toISODate(baseDate))) {
            baseDate = new Date(baseDate.getFullYear(), baseDate.getMonth(), baseDate.getDate() + 1);
        }
        pickerDate = selectedDate || toISODate(baseDate);
        viewYear = parseISODate(pickerDate).getFullYear();
        viewMonth = parseISODate(pickerDate).getMonth();
        populateYearSelect();
        renderDateCalendar();
        openSheet(dateSheet);
    }

    function setStep(step) {
        currentStep = step;

        steps.forEach(function (el) {
            var stepNumber = Number(el.dataset.step);
            el.hidden = stepNumber !== currentStep;
        });

        tabs.forEach(function (tab) {
            var tabStep = Number(tab.dataset.tab);
            var isActive = tabStep === currentStep;
            tab.classList.toggle('create-event__tab--active', isActive);
            tab.setAttribute('aria-selected', String(isActive));
            tab.disabled = isEditMode ? false : tabStep > currentStep;
        });

        if (nextBtn) {
            nextBtn.hidden = currentStep === maxStep;
        }
        if (submitBtn) {
            submitBtn.hidden = currentStep !== maxStep;
        }
        if (backBtn) {
            backBtn.hidden = currentStep === 1;
        }
    }

    function validateStep(step) {
        if (step === 1) {
            if (!sportSelect || !sportSelect.value) {
                alert('Выберите вид спорта');
                return false;
            }
            var players = maxPlayersInput ? Number(maxPlayersInput.value) : 0;
            if (!players || players < minPlayers) {
                alert('Укажите количество участников (минимум ' + minPlayers + ')');
                if (maxPlayersInput) {
                    maxPlayersInput.focus();
                }
                return false;
            }
            if (!placeInput || !placeInput.value.trim()) {
                alert('Укажите площадку');
                return false;
            }
            var lat = document.getElementById('id_latitude');
            var lon = document.getElementById('id_longitude');
            if (!lat || !lon || !lat.value || !lon.value) {
                alert('Выберите место на карте в разделе «Площадка»');
                return false;
            }
        }

        if (step === 2) {
            if (!selectedDate) {
                alert('Укажите дату');
                return false;
            }
            if (!selectedTime) {
                alert('Укажите время начала');
                return false;
            }
            if (isPastDateTime(selectedDate, selectedTime)) {
                alert('Время начала игры должно быть в будущем');
                return false;
            }
            if (!durationInput || !durationInput.value || getDurationHours() <= 0) {
                alert('Укажите продолжительность');
                return false;
            }
        }

        if (step === 3) {
            if (priceInput && priceInput.value !== '') {
                var totalPrice = Number(priceInput.value);
                if (Number.isNaN(totalPrice) || totalPrice < 0) {
                    alert('Стоимость не может быть отрицательной');
                    priceInput.focus();
                    return false;
                }
            }
        }

        return true;
    }

    if (sportTrigger) {
        sportTrigger.addEventListener('click', function () {
            openSheet(sportSheet);
        });
        sportTrigger.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openSheet(sportSheet);
            }
        });
    }

    sportItems.forEach(function (item) {
        item.addEventListener('click', function () {
            if (!sportSelect) {
                return;
            }
            sportSelect.value = item.dataset.sportValue;
            syncSportLabel();
            closeSheet(sportSheet);
        });
    });

    function skillIndexFromValue(value) {
        for (var i = 0; i < skillLevels.length; i += 1) {
            if (skillLevels[i].value === value) {
                return i;
            }
        }
        return 0;
    }

    function syncSkillUI() {
        var level = skillLevels[skillIndex] || skillLevels[0];
        if (skillSelect) {
            skillSelect.value = skillToggle && skillToggle.checked ? level.value : '';
        }
        if (skillLabel) {
            skillLabel.textContent = level.label;
        }
        if (skillSlider) {
            skillSlider.setAttribute('aria-valuenow', String(skillIndex));
            skillSlider.setAttribute('aria-valuetext', level.label);
        }
        var percent = skillLevels.length > 1
            ? (skillIndex / (skillLevels.length - 1)) * 100
            : 0;
        if (skillFill) {
            skillFill.style.width = percent + '%';
        }
        if (skillThumb) {
            skillThumb.style.left = percent + '%';
        }
        skillDots.forEach(function (dot) {
            var idx = Number(dot.dataset.skillDot);
            dot.classList.toggle('is-active', idx <= skillIndex);
        });
        skillItems.forEach(function (item) {
            item.classList.toggle(
                'is-selected',
                item.dataset.skillValue === level.value
            );
        });
    }

    function setSkillIndex(index) {
        skillIndex = Math.max(0, Math.min(skillLevels.length - 1, index));
        syncSkillUI();
    }

    function syncSkillPanelVisibility() {
        var enabled = !!(skillToggle && skillToggle.checked);
        if (skillPanel) {
            skillPanel.hidden = !enabled;
        }
        if (enabled) {
            if (skillSelect && skillSelect.value) {
                skillIndex = skillIndexFromValue(skillSelect.value);
            }
            syncSkillUI();
        } else if (skillSelect) {
            skillSelect.value = '';
        }
    }

    function skillIndexFromPointer(clientX) {
        if (!skillSlider) {
            return skillIndex;
        }
        var track = skillSlider.querySelector('.create-event__skill-track') || skillSlider;
        var rect = track.getBoundingClientRect();
        var ratio = (clientX - rect.left) / Math.max(1, rect.width);
        ratio = Math.max(0, Math.min(1, ratio));
        return Math.round(ratio * (skillLevels.length - 1));
    }

    if (skillToggle) {
        skillToggle.addEventListener('change', function () {
            if (skillToggle.checked && skillSelect && !skillSelect.value) {
                skillIndex = 0;
            }
            syncSkillPanelVisibility();
        });
    }

    if (skillSlider) {
        skillSlider.addEventListener('pointerdown', function (event) {
            event.preventDefault();
            event.stopPropagation();
            setSkillIndex(skillIndexFromPointer(event.clientX));

            function onMove(moveEvent) {
                moveEvent.preventDefault();
                setSkillIndex(skillIndexFromPointer(moveEvent.clientX));
            }

            function onUp(upEvent) {
                if (upEvent) {
                    upEvent.preventDefault();
                }
                window.removeEventListener('pointermove', onMove);
                window.removeEventListener('pointerup', onUp);
                window.removeEventListener('pointercancel', onUp);
            }

            window.addEventListener('pointermove', onMove);
            window.addEventListener('pointerup', onUp);
            window.addEventListener('pointercancel', onUp);
        });

        skillSlider.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();
        });

        skillSlider.addEventListener('keydown', function (event) {
            if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
                event.preventDefault();
                setSkillIndex(skillIndex + 1);
            } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
                event.preventDefault();
                setSkillIndex(skillIndex - 1);
            } else if (event.key === 'Home') {
                event.preventDefault();
                setSkillIndex(0);
            } else if (event.key === 'End') {
                event.preventDefault();
                setSkillIndex(skillLevels.length - 1);
            }
        });
    }

    skillItems.forEach(function (item) {
        item.addEventListener('click', function () {
            setSkillIndex(skillIndexFromValue(item.dataset.skillValue));
            closeSheet(skillSheet);
        });
    });

    if (skillSelect && skillSelect.value) {
        skillIndex = skillIndexFromValue(skillSelect.value);
    }
    syncSkillPanelVisibility();

    if (venueTrigger) {
        venueTrigger.addEventListener('click', function () {
            if (venueInput && placeInput) {
                venueInput.value = placeInput.value;
            }
            openSheet(venueSheet);
            document.dispatchEvent(new CustomEvent('create-game:init-map', {
                detail: { mapId: 'create-game-map', statusId: 'map-status-text-sheet' }
            }));
        });
        venueTrigger.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                venueTrigger.click();
            }
        });
    }

    if (venueConfirm) {
        venueConfirm.addEventListener('click', function () {
            if (venueInput && placeInput) {
                placeInput.value = venueInput.value.trim();
            }
            syncVenueLabel();
            closeSheet(venueSheet);
        });
    }

    if (venueInput) {
        venueInput.addEventListener('input', function () {
            if (placeInput) {
                placeInput.value = venueInput.value.trim();
            }
        });
    }

    if (dateTrigger) {
        dateTrigger.addEventListener('click', openDateSheet);
        dateTrigger.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openDateSheet();
            }
        });
    }

    if (dateConfirm) {
        dateConfirm.addEventListener('click', function () {
            if (!pickerDate) {
                return;
            }
            selectedDate = pickerDate;
            if (selectedTime && isPastDateTime(selectedDate, selectedTime)) {
                selectedTime = null;
            }
            updateDateTimeLabels();
            updateStartTimeValue();
            closeSheet(dateSheet);
        });
    }

    if (datePrevMonth) {
        datePrevMonth.addEventListener('click', function () {
            var nextMonth = viewMonth - 1;
            var nextYear = viewYear;
            if (nextMonth < 0) {
                nextMonth = 11;
                nextYear -= 1;
            }
            if (isMonthInPast(nextYear, nextMonth)) {
                return;
            }
            viewMonth = nextMonth;
            viewYear = nextYear;
            renderDateCalendar();
        });
    }

    if (dateNextMonth) {
        dateNextMonth.addEventListener('click', function () {
            viewMonth += 1;
            if (viewMonth > 11) {
                viewMonth = 0;
                viewYear += 1;
            }
            renderDateCalendar();
        });
    }

    if (dateYearSelect) {
        dateYearSelect.addEventListener('change', function () {
            var nextYear = Number(dateYearSelect.value);
            if (isMonthInPast(nextYear, viewMonth)) {
                viewMonth = new Date().getMonth();
            }
            viewYear = nextYear;
            renderDateCalendar();
        });
    }

    if (timeTrigger) {
        timeTrigger.addEventListener('click', openTimeSheet);
        timeTrigger.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openTimeSheet();
            }
        });
    }

    if (timeHourDisplay) {
        timeHourDisplay.addEventListener('click', function () {
            timePickerMode = 'hour';
            renderTimePicker();
        });
    }

    if (timeMinuteDisplay) {
        timeMinuteDisplay.addEventListener('click', function () {
            timePickerMode = 'minute';
            renderTimePicker();
        });
    }

    if (timeConfirm) {
        timeConfirm.addEventListener('click', function () {
            var pickedTime = formatPickerTime();
            if (selectedDate && isPastDateTime(selectedDate, pickedTime)) {
                alert('Время начала игры должно быть в будущем');
                return;
            }
            selectedTime = pickedTime;
            updateDateTimeLabels();
            updateStartTimeValue();
            closeSheet(timeSheet);
        });
    }

    durationButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            var hours = button.dataset.durationHours;
            if (!hours) {
                return;
            }
            setDurationHours(hours);
            updateDurationLabel();
            updateStartTimeValue();
        });
    });

    root.querySelectorAll('[data-sheet-close]').forEach(function (el) {
        el.addEventListener('click', function () {
            closeAllSheets();
        });
    });

    if (nextBtn) {
        nextBtn.addEventListener('click', function () {
            if (!validateStep(currentStep)) {
                return;
            }
            if (currentStep < maxStep) {
                setStep(currentStep + 1);
            }
        });
    }

    if (backBtn) {
        backBtn.addEventListener('click', function () {
            if (currentStep > 1) {
                setStep(currentStep - 1);
            }
        });
    }

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            var targetStep = Number(tab.dataset.tab);
            if (isEditMode || targetStep <= currentStep) {
                setStep(targetStep);
            }
        });
    });

    if (form) {
        form.addEventListener('submit', function (event) {
            if (!validateStep(1) || !validateStep(2) || !validateStep(3)) {
                event.preventDefault();
                if (!validateStep(1)) {
                    setStep(1);
                } else if (!validateStep(2)) {
                    setStep(2);
                } else {
                    setStep(3);
                }
            }
        });
    }

    if (maxPlayersInput && !maxPlayersInput.value) {
        maxPlayersInput.value = '0';
    }
    if (maxPlayersInput) {
        maxPlayersInput.addEventListener('input', updatePricePerPlayer);
    }
    if (priceInput) {
        priceInput.addEventListener('input', updatePricePerPlayer);
    }

    if (startTimeInput && startTimeInput.value) {
        var parts = startTimeInput.value.split(' ');
        if (parts.length === 2) {
            var datePart = parts[0].split('.');
            if (datePart.length === 3) {
                selectedDate = [datePart[2], datePart[1], datePart[0]].join('-');
            }
            selectedTime = parts[1];
        }
    }

    if (durationInput) {
        setDurationHours(durationInput.value || 1);
    }

    syncSportLabel();
    syncVenueLabel();
    updateDateTimeLabels();
    updateDurationLabel();
    updatePricePerPlayer();

    var initialStep = Number(root.dataset.initialStep) || 1;
    setStep(initialStep);

    if (root.dataset.hasErrors) {
        var errorEl = root.querySelector('.create-event__field-error, .create-event__form-alert');
        if (errorEl) {
            errorEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
});
