// Мультифайловый импорт заочного расписания.
//
// Файлы по очереди отправляются в парсер (расписание-парсер на порту 8001),
// ответ превращается в «запись»: набор групп + пары по датам (ключ ячейки
// «ДД.ММ.ГГГГ_№ пары»). Записи с одинаковым набором групп перезаписываются.
// Сетка динамическая: даты и пары можно добавлять и убирать вручную.
// Кнопка «Загрузить» отправляет все записи разом: сохранившиеся исчезают
// из списка, записи с ошибками валидации подсвечиваются красным.

const PARSER_URL = `http://${window.location.hostname}:8001/schedule/parser/schedule/parse`;

const entries = [];            // записи: {key, groups, dates, cells, fileName, errors | parseError}
let selectedEntryIndex = null;
let parseErrorSeq = 0;

const CELL_FIELDS = ['discipline', 'format', 'teacher', 'auditorium'];
const LESSON_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8];
const WEEKDAY_NAMES = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];

async function importSchedules() {
    const fileInput = document.getElementById("ScheduleFile");
    const files = Array.from(fileInput.files || []);
    if (!files.length) {
        showUploadError('Не выбран ни один файл');
        return;
    }
    hideUploadError();
    for (const file of files) {
        const formData = new FormData();
        formData.append("excel_table", file);
        formData.append("education_form", "part_time");
        formData.append("education_type", "higher_education");
        try {
            const response = await fetch(PARSER_URL, {method: "POST", body: formData});
            const result = await response.json();
            if (response.ok) {
                addParsedResults(file.name, result);
            } else {
                addParseErrorEntry(file.name, formatParserError(result));
            }
        } catch (error) {
            console.error("Ошибка обращения к парсеру:", error);
            addParseErrorEntry(file.name, `Парсер недоступен (${error.message}). ` +
                `Убедитесь, что сервис запущен на порту 8001.`);
        }
    }
    fileInput.value = '';
    if (selectedEntryIndex === null) {
        const first = entries.findIndex(e => e.cells);
        if (first !== -1) selectEntry(first, {skipCollect: true});
    }
    renderEntries();
    updateSaveButton();
}

function formatParserError(result) {
    const details = result && result.details;
    if (!details) return 'Не удалось разобрать файл';
    const messages = Object.values(details).map(v => Array.isArray(v) ? v.join('; ') : String(v));
    return messages.join('; ');
}

function addParsedResults(fileName, result) {
    (result.results || []).forEach(scheduleResult => {
        let groups = scheduleResult.groups;
        if (typeof groups === 'string') {
            groups = groups.split(',');
        }
        groups = (groups || []).map(g => String(g).trim()).filter(Boolean);
        const cells = scheduleToCells(scheduleResult.schedule);
        upsertEntry(groups, cells, fileName);
    });
}

// schedule парсера заочной формы: {"ДД.ММ.ГГГГ": [{number, is_special, ...}, ...]}
function scheduleToCells(schedule) {
    const cells = {};
    for (const dateKey in schedule) {
        (schedule[dateKey] || []).forEach(lesson => {
            cells[`${dateKey}_${lesson.number}`] = {
                is_special: !!lesson.is_special,
                discipline: lesson.discipline_title || '',
                format: lesson.format || '',
                teacher: lesson.teacher_name || '',
                auditorium: (lesson.auditorium_number === null || lesson.auditorium_number === undefined)
                    ? '' : lesson.auditorium_number
            };
        });
    }
    return cells;
}

function entryKey(groups) {
    return [...groups].map(g => g.toLowerCase()).sort().join(',');
}

function upsertEntry(groups, cells, fileName) {
    const key = entryKey(groups);
    const existing = entries.findIndex(e => e.key === key);
    if (existing !== -1) {
        // файл с теми же группами: расписание перезаписывается, дубль не создаётся
        Object.assign(entries[existing], {groups, cells, fileName, errors: null});
        entries[existing].dates = datesFromCells(cells);
        if (selectedEntryIndex === existing) selectEntry(existing, {skipCollect: true});
        return existing;
    }
    entries.push({key, groups, dates: datesFromCells(cells), cells, fileName, errors: null});
    return entries.length - 1;
}

function addParseErrorEntry(fileName, errorText) {
    entries.push({key: `__parse_error_${++parseErrorSeq}`, groups: [], dates: [], cells: null,
                  fileName, parseError: errorText});
}

function datesFromCells(cells) {
    const set = new Set(Object.keys(cells).map(key => key.split('_')[0]));
    return sortDates([...set]);
}

function sortDates(dates) {
    return [...new Set(dates)].sort((a, b) => parseDisplayDate(a) - parseDisplayDate(b));
}

function parseDisplayDate(dateStr) {
    const [d, m, y] = dateStr.split('.');
    return new Date(+y, +m - 1, +d);
}

function weekdayLabel(dateStr) {
    const date = parseDisplayDate(dateStr);
    return WEEKDAY_NAMES[date.getDay()];
}

function selectEntry(index, {skipCollect = false} = {}) {
    if (!skipCollect) collectGridToCells();
    selectedEntryIndex = index;
    renderGrid(entries[index]);
    showEntryErrors(entries[index]);
    renderEntries();
}

// ---------------------------------------------------------------------------
// Динамическая сетка: секция на каждую дату, строки-пары внутри
// ---------------------------------------------------------------------------

function renderGrid(entry) {
    const container = document.getElementById('schedule-container');
    container.innerHTML = '';
    if (!entry.cells) return;

    // шапка колонок
    const header = document.createElement('div');
    header.className = 'input-group';
    header.innerHTML = `
        <span class="input-group-text" style="min-width: 70px;">№</span>
        <span class="input-group-text px-3"> *</span>
        <input type="text" class="form-control" disabled readonly value="Дисциплина">
        <input type="text" class="form-control" disabled readonly value="Формат" style="max-width:250px">
        <input type="text" class="form-control" disabled readonly value="Преподаватель" style="max-width:200px">
        <input type="text" class="form-control" disabled readonly value="Ауд." style="max-width:60px">
        <span class="input-group-text" style="min-width: 38px;"></span>`;
    container.appendChild(header);

    const byDate = {};
    for (const key in entry.cells) {
        const [date] = key.split('_');
        (byDate[date] = byDate[date] || []).push(key);
    }
    const dates = sortDates([...(entry.dates || []), ...Object.keys(byDate)]);
    dates.forEach(date => {
        const section = buildDateSection(date);
        (byDate[date] || []).sort((a, b) => cellNumber(a) - cellNumber(b)).forEach(key => {
            section.querySelector('.pt-rows')
                .appendChild(buildLessonRow(date, cellNumber(key), entry.cells[key]));
        });
        container.appendChild(section);
    });
    if (!dates.length) {
        const hint = document.createElement('p');
        hint.className = 'text-muted mt-2';
        hint.textContent = 'Нет ни одной даты: загрузите файл или добавьте дату вручную.';
        container.appendChild(hint);
    }
}

function cellNumber(key) {
    return Number(key.split('_')[1]) || 0;
}

function buildDateSection(date) {
    const section = document.createElement('div');
    section.className = 'pt-date-section';
    section.dataset.date = date;

    const header = document.createElement('div');
    header.className = 'd-flex justify-content-between align-items-center mt-3 mb-1';
    const title = document.createElement('strong');
    title.textContent = `${weekdayLabel(date)}, ${date}`;
    const buttons = document.createElement('div');
    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'btn btn-sm btn-outline-dark';
    addBtn.textContent = '+ пара';
    addBtn.onclick = () => addLessonRow(date);
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-sm btn-outline-danger ms-2';
    removeBtn.textContent = '×';
    removeBtn.title = 'Убрать дату';
    removeBtn.onclick = () => removeDate(date);
    buttons.append(addBtn, removeBtn);
    header.append(title, buttons);

    const rows = document.createElement('div');
    rows.className = 'pt-rows';
    section.append(header, rows);
    return section;
}

function buildLessonRow(date, number, cell) {
    cell = cell || {is_special: false, discipline: '', format: '', teacher: '', auditorium: ''};
    const row = document.createElement('div');
    row.className = 'input-group pt-lesson-row';
    row.dataset.date = date;

    const select = document.createElement('select');
    select.className = 'form-select pt-lesson-number';
    select.style.maxWidth = '70px';
    LESSON_NUMBERS.forEach(n => {
        const option = document.createElement('option');
        option.value = String(n);
        option.textContent = String(n);
        select.appendChild(option);
    });
    select.value = String(number || 1);
    row.appendChild(select);

    const specialBox = document.createElement('div');
    specialBox.className = 'input-group-text';
    const special = document.createElement('input');
    special.type = 'checkbox';
    special.className = 'form-check-input mt-0 pt-cell';
    special.dataset.field = 'is_special';
    special.checked = !!cell.is_special;
    specialBox.appendChild(special);
    row.appendChild(specialBox);

    CELL_FIELDS.forEach(field => {
        const input = document.createElement(field === 'discipline' ? 'textarea' : 'input');
        input.className = 'form-control pt-cell';
        input.dataset.field = field;
        if (field === 'discipline') {
            input.rows = 1;
        } else {
            input.type = 'text';
            if (field === 'format') input.style.maxWidth = '250px';
            if (field === 'teacher') input.style.maxWidth = '200px';
            if (field === 'auditorium') input.style.maxWidth = '60px';
        }
        input.value = cell[field] !== undefined && cell[field] !== null ? cell[field] : '';
        row.appendChild(input);
    });

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-outline-danger';
    removeBtn.textContent = '×';
    removeBtn.title = 'Убрать пару';
    removeBtn.style.maxWidth = '38px';
    removeBtn.onclick = event => removeRow(event.target);
    row.appendChild(removeBtn);
    return row;
}

function addLessonRow(date) {
    const section = findDateSection(date);
    if (!section) return;
    const row = buildLessonRow(date, null, null);
    // первый свободный номер на эту дату
    const used = new Set([...section.querySelectorAll('.pt-lesson-number')].map(s => s.value));
    const free = LESSON_NUMBERS.find(n => !used.has(String(n)));
    row.querySelector('.pt-lesson-number').value = String(free || LESSON_NUMBERS.length);
    section.querySelector('.pt-rows').appendChild(row);
    row.querySelector('.pt-cell').focus();
}

function findDateSection(date) {
    return document.querySelector(`#schedule-container .pt-date-section[data-date="${date}"]`);
}

function addDateFromInput() {
    const input = document.getElementById('pt-new-date');
    if (!input.value) return;
    const [y, m, d] = input.value.split('-');
    const date = `${d}.${m}.${y}`;
    if (findDateSection(date)) return;  // дата уже есть
    // если сетка ещё пустая (не выбрана запись) — дату добавить нельзя
    if (selectedEntryIndex === null || !entries[selectedEntryIndex].cells) {
        showUploadError('Сначала загрузите файл и выберите запись в списке');
        return;
    }
    collectGridToCells();
    const entry = entries[selectedEntryIndex];
    entry.dates = sortDates([...(entry.dates || []), date]);
    renderGrid(entry);
    showEntryErrors(entry);
    input.value = '';
}

function removeDate(date) {
    collectGridToCells();
    const entry = entries[selectedEntryIndex];
    if (!entry || !entry.cells) return;
    entry.dates = (entry.dates || []).filter(d => d !== date);
    for (const key of Object.keys(entry.cells)) {
        if (key.split('_')[0] === date) delete entry.cells[key];
    }
    renderGrid(entry);
    showEntryErrors(entry);
    updateSaveButton();
}

function removeRow(button) {
    const row = button.closest('.pt-lesson-row');
    if (row) row.remove();
}

function collectGridToCells() {
    if (selectedEntryIndex === null) return;
    const entry = entries[selectedEntryIndex];
    if (!entry.cells) return;
    const cells = {};
    document.querySelectorAll('#schedule-container .pt-lesson-row').forEach(row => {
        const date = row.dataset.date;
        const number = row.querySelector('.pt-lesson-number').value;
        const cell = {is_special: false, discipline: '', format: '', teacher: '', auditorium: ''};
        row.querySelectorAll('.pt-cell').forEach(el => {
            if (el.dataset.field === 'is_special') cell.is_special = el.checked;
            else cell[el.dataset.field] = el.value.trim();
        });
        // пустые строки не отправляем; при совпадении номера последняя строка выигрывает
        if (cell.discipline || cell.format || cell.teacher || cell.auditorium) {
            cells[`${date}_${number}`] = cell;
        }
    });
    entry.cells = cells;
    entry.dates = [...document.querySelectorAll('#schedule-container .pt-date-section')]
        .map(section => section.dataset.date);
}

// ---------------------------------------------------------------------------
// Список записей, сохранение, подсветка ошибок — как в очном импорте
// ---------------------------------------------------------------------------

function removeEntry(event, index) {
    event.preventDefault();
    event.stopPropagation();
    entries.splice(index, 1);
    if (selectedEntryIndex === index) {
        selectedEntryIndex = null;
        document.getElementById('schedule-container').innerHTML = '';
        clearCellErrors();
        const next = entries.findIndex(e => e.cells);
        if (next !== -1) selectEntry(next, {skipCollect: true});
    } else if (selectedEntryIndex > index) {
        selectedEntryIndex--;
    }
    renderEntries();
    updateSaveButton();
}

function renderEntries() {
    const list = document.getElementById('importEntriesList');
    list.innerHTML = '';
    entries.forEach((entry, index) => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action';
        if (entry.parseError || entry.errors) item.classList.add('list-group-item-danger');
        if (index === selectedEntryIndex) item.classList.add('entry-active');
        item.onclick = (e) => {
            e.preventDefault();
            if (entry.cells) selectEntry(index);
        };
        const title = document.createElement('div');
        title.className = 'd-flex justify-content-between align-items-start';
        const titleText = document.createElement('span');
        titleText.textContent = entry.groups.length ? entry.groups.join(', ') : 'Ошибка разбора файла';
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close';
        closeBtn.style.fontSize = '10px';
        closeBtn.title = 'Убрать из списка';
        closeBtn.onclick = (e) => removeEntry(e, index);
        title.append(titleText, closeBtn);
        item.appendChild(title);
        const fileName = document.createElement('div');
        fileName.className = 'small text-muted text-truncate';
        fileName.textContent = entry.fileName;
        fileName.title = entry.fileName;
        item.appendChild(fileName);
        const errorText = entry.parseError ||
            (entry.errors && entry.errors._group ? entry.errors._group.join('; ') : null) ||
            (entry.errors ? 'Есть ошибки в парах — откройте запись, чтобы увидеть' : null);
        if (errorText) {
            const errDiv = document.createElement('div');
            errDiv.className = 'small';
            errDiv.style.color = '#dc3545';
            errDiv.textContent = errorText;
            item.appendChild(errDiv);
        }
        list.appendChild(item);
    });
}

function updateSaveButton() {
    document.getElementById('saveSchedulesBtn').disabled =
        !entries.some(e => e.cells);
}

function showEntryErrors(entry) {
    clearCellErrors();
    const box = document.getElementById('pt-import-cell-errors');
    box.innerHTML = '';
    if (!entry.errors) return;
    const messages = [];
    (entry.errors._group || []).forEach(m => messages.push(m));
    document.querySelectorAll('#schedule-container .pt-lesson-row').forEach(row => {
        const key = `${row.dataset.date}_${row.querySelector('.pt-lesson-number').value}`;
        if (entry.errors[key]) {
            entry.errors[key].forEach(m => messages.push(m));
            row.classList.add('cell-error');
        }
    });
    if (messages.length) {
        box.innerHTML = `<p class="alert alert-danger mb-0" style="white-space: pre-line">${messages.join('\n')}</p>`;
    }
}

function clearCellErrors() {
    document.querySelectorAll('#schedule-container .cell-error').forEach(el => el.classList.remove('cell-error'));
    document.getElementById('pt-import-cell-errors').innerHTML = '';
}

async function saveSchedules() {
    collectGridToCells();
    const saveable = [];
    entries.forEach((entry, index) => {
        if (entry.cells) saveable.push({entry, index});
    });
    if (!saveable.length) {
        showSummary('danger', 'Нет записей для сохранения');
        return;
    }
    const button = document.getElementById('saveSchedulesBtn');
    button.disabled = true;
    button.textContent = 'Загрузка...';
    try {
        const response = await fetch(document.getElementById('importSaveUrl').value, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({entries: saveable.map(({entry}) => ({groups: entry.groups, cells: entry.cells}))})
        });
        const result = await response.json();
        if (!response.ok) {
            showSummary('danger', result.error || 'Ошибка сохранения');
            return;
        }
        applySaveResults(result.results || [], saveable);
    } catch (error) {
        console.error('Ошибка сохранения:', error);
        showSummary('danger', `Ошибка сохранения: ${error.message}`);
    } finally {
        button.textContent = 'Загрузить';
        updateSaveButton();
    }
}

function applySaveResults(results, saveable) {
    const savedGroups = [];
    let failedCount = 0;
    // удаляем с конца, чтобы индексы в entries не сместились
    const removals = [];
    results.forEach((r, order) => {
        const {entry, index} = saveable[order];
        if (r.status === 'saved') {
            savedGroups.push(...(r.groups || []));
            removals.push(index);
        } else {
            entry.errors = r.errors || {_group: ['Неизвестная ошибка']};
            failedCount++;
        }
    });
    removals.sort((a, b) => b - a).forEach(index => {
        entries.splice(index, 1);
        if (selectedEntryIndex === index) {
            selectedEntryIndex = null;
            document.getElementById('schedule-container').innerHTML = '';
            clearCellErrors();
        } else if (selectedEntryIndex > index) {
            selectedEntryIndex--;
        }
    });
    if (selectedEntryIndex === null) {
        const first = entries.findIndex(e => e.cells);
        if (first !== -1) selectEntry(first, {skipCollect: true});
    } else {
        showEntryErrors(entries[selectedEntryIndex]);
    }
    renderEntries();
    updateSaveButton();
    if (failedCount === 0) {
        showSummary('success',
            `Расписание загружено для групп: ${savedGroups.join(', ')}. ` +
            'Записи без ошибок убраны из списка.');
    } else {
        showSummary('warning',
            `Загружено групп: ${savedGroups.length ? savedGroups.join(', ') : '—'}. ` +
            `Осталось записей с ошибками: ${failedCount} (подсвечены красным).`);
    }
}

function showSummary(type, text) {
    const box = document.getElementById('pt-import-summary');
    box.innerHTML = `<p class="alert alert-${type} mt-2 mb-2">${text}</p>`;
}

function showUploadError(text) {
    const el = document.getElementById('pt-import-upload-error');
    el.textContent = text;
    el.style.display = 'block';
}

function hideUploadError() {
    document.getElementById('pt-import-upload-error').style.display = 'none';
}
