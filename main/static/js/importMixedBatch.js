// Мультифайловый импорт очно-заочного расписания.
//
// Файлы по очереди отправляются в парсер (расписание-парсер на порту 8001)
// как очные: файлы очно-заочной формы содержат ту же недельную сетку на
// 2 недели. Многостраничные файлы разбираются по листам: каждый лист —
// отдельная запись, подписанная названием листа. Если название листа —
// диапазон дат («01.09-27.09.26»), интервал записи заполняется из него;
// иначе интервал берётся из полей «по умолчанию» (и правится вручную).
// Записи с одинаковым набором групп (одним листом) перезаписываются.
// Кнопка «Загрузить» отправляет все записи разом: сохранившиеся исчезают
// из списка, ошибочные подсвечиваются красным.

const PARSER_URL = `http://${window.location.hostname}:8001/schedule/parser/schedule/parse`;

const entries = [];            // записи: {key, groups, cells, dateStart, dateEnd, fileName, sheetLabel, errors | parseError}
let selectedEntryIndex = null;
let parseErrorSeq = 0;

const WEEK_DAYS = {
    "понедельник": "пн",
    "вторник": "вт",
    "среда": "ср",
    "четверг": "чт",
    "пятница": "пт",
    "суббота": "сб",
    "воскресенье": "вс"
};
const WEEK_NUMBERS = {
    "first_week": 1,
    "second_week": 2
};
const CELL_FIELDS = ['discipline', 'format', 'teacher', 'auditorium'];

async function importSchedules() {
    const fileInput = document.getElementById("ScheduleFile");
    const files = Array.from(fileInput.files || []);
    if (!files.length) {
        showUploadError('Не выбран ни один файл');
        return;
    }
    hideUploadError();
    // интервал по умолчанию — применяется к новым записям
    const defaultStart = document.getElementById('defaultDateStart').value;
    const defaultEnd = document.getElementById('defaultDateEnd').value;
    for (const file of files) {
        const formData = new FormData();
        formData.append("excel_table", file);
        // файлы очно-заочной формы парсятся очным парсером (недельная сетка)
        formData.append("education_form", "full_time");
        formData.append("education_type", "higher_education");
        try {
            const response = await fetch(PARSER_URL, {method: "POST", body: formData});
            const result = await response.json();
            if (response.ok) {
                addParsedResults(file.name, result, defaultStart, defaultEnd);
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

// Название листа вида «01.09-27.09.26» / «01.12-10.01.27» -> интервал дат.
// Год не угадываем: если года нет ни у одной даты — интервал не заполняем.
function parseSheetDateRange(sheetName) {
    if (!sheetName) return null;
    const m = String(sheetName).match(
        /(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?(?:\s*[-–—]\s*|\s+по\s+)(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?/);
    if (!m) return null;
    const toYear = (value) => {
        if (value === undefined) return null;
        let year = parseInt(value, 10);
        if (year < 100) year += 2000;
        return year;
    };
    const day1 = parseInt(m[1], 10), month1 = parseInt(m[2], 10);
    const day2 = parseInt(m[4], 10), month2 = parseInt(m[5], 10);
    let year1 = toYear(m[3]), year2 = toYear(m[6]);
    if (year1 === null && year2 === null) return null;
    // начало в декабре, конец в январе — у более поздней даты следующий год
    if (year1 === null) year1 = month1 > month2 ? year2 - 1 : year2;
    if (year2 === null) year2 = month1 > month2 ? year1 + 1 : year1;
    const iso = (year, month, day) =>
        `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const start = iso(year1, month1, day1), end = iso(year2, month2, day2);
    if (isNaN(new Date(start)) || isNaN(new Date(end))) return null;
    return {start, end};
}

function addParsedResults(fileName, result, defaultStart, defaultEnd) {
    const results = result.results || [];
    // в многостраничном файле записи различаются названием листа
    const multi = results.length > 1;
    results.forEach(scheduleResult => {
        let groups = scheduleResult.groups;
        if (typeof groups === 'string') {
            groups = groups.split(',');
        }
        groups = (groups || []).map(g => String(g).trim()).filter(Boolean);
        const cells = scheduleToCells(scheduleResult.schedule);
        const sheetName = scheduleResult.sheet_name || null;
        const sheetDates = parseSheetDateRange(sheetName);
        upsertEntry(groups, cells, fileName, sheetName, multi, sheetDates,
                    defaultStart, defaultEnd);
    });
}

function scheduleToCells(schedule) {
    const cells = {};
    for (const weekKey in schedule) {
        const week = WEEK_NUMBERS[weekKey];
        if (!week) continue;
        for (const dayKey in schedule[weekKey]) {
            const day = WEEK_DAYS[dayKey];
            if (!day) continue;
            (schedule[weekKey][dayKey] || []).forEach(lesson => {
                cells[`${week}_${day}_${lesson.number}`] = {
                    is_special: !!lesson.is_special,
                    discipline: lesson.discipline_title || '',
                    format: lesson.format || '',
                    teacher: lesson.teacher_name || '',
                    auditorium: (lesson.auditorium_number === null || lesson.auditorium_number === undefined)
                        ? '' : lesson.auditorium_number
                };
            });
        }
    }
    return cells;
}

function entryKey(groups, sheetName, multi) {
    const base = [...groups].map(g => g.toLowerCase()).sort().join(',');
    // в многостраничном файле каждый лист — отдельная запись
    return multi && sheetName ? `${base}|${sheetName.toLowerCase()}` : base;
}

function upsertEntry(groups, cells, fileName, sheetName, multi, sheetDates,
                     defaultStart, defaultEnd) {
    const key = entryKey(groups, sheetName, multi);
    const dateStart = sheetDates ? sheetDates.start : (defaultStart || '');
    const dateEnd = sheetDates ? sheetDates.end : (defaultEnd || '');
    // подпись листа: показываем, если из него взят интервал или лист не один
    const sheetLabel = sheetName && (sheetDates || multi) ? sheetName : null;
    const existing = entries.findIndex(e => e.key === key);
    if (existing !== -1) {
        // тот же файл/лист с теми же группами: перезапись, дубль не создаётся
        Object.assign(entries[existing], {groups, cells, fileName, sheetLabel,
                                          dateStart, dateEnd, errors: null});
        if (selectedEntryIndex === existing) selectEntry(existing, {skipCollect: true});
        return existing;
    }
    entries.push({key, groups, cells, dateStart, dateEnd, fileName, sheetLabel,
                  errors: null});
    return entries.length - 1;
}

function addParseErrorEntry(fileName, errorText) {
    entries.push({key: `__parse_error_${++parseErrorSeq}`, groups: [], cells: null,
                  fileName, parseError: errorText});
}

function selectEntry(index, {skipCollect = false} = {}) {
    if (!skipCollect) collectGridToCells();
    selectedEntryIndex = index;
    fillGridFromCells(entries[index].cells || {});
    showEntryErrors(entries[index]);
    renderEntries();
}

function fillGridFromCells(cells) {
    document.getElementById('scheduleForm').reset();
    for (const key in cells) {
        const cell = cells[key];
        const special = document.getElementById(`${key}_is_special`);
        if (special) special.checked = !!cell.is_special;
        CELL_FIELDS.forEach(field => {
            const el = document.getElementById(`${key}_${field}`);
            if (el) el.value = cell[field] !== undefined && cell[field] !== null ? cell[field] : '';
        });
    }
}

function collectGridToCells() {
    if (selectedEntryIndex === null) return;
    const entry = entries[selectedEntryIndex];
    if (!entry.cells) return;
    const cells = {};
    document.querySelectorAll('#scheduleForm [name]').forEach(el => {
        const parts = el.name.split('_');
        if (parts.length !== 4) return;
        const [week, day, number, field] = parts;
        const key = `${week}_${day}_${number}`;
        cells[key] = cells[key] || {is_special: false, discipline: '', format: '', teacher: '', auditorium: ''};
        if (field === 'is_special') {
            cells[key].is_special = el.checked;
        } else {
            cells[key][field] = el.value.trim();
        }
    });
    // пустые ячейки не отправляем
    entry.cells = Object.fromEntries(Object.entries(cells).filter(([, cell]) =>
        cell.discipline || cell.format || cell.teacher || cell.auditorium));
}

function removeEntry(event, index) {
    event.preventDefault();
    event.stopPropagation();
    entries.splice(index, 1);
    if (selectedEntryIndex === index) {
        selectedEntryIndex = null;
        document.getElementById('scheduleForm').reset();
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
        const baseLabel = entry.groups.length ? entry.groups.join(', ') : 'Ошибка разбора файла';
        titleText.textContent = entry.sheetLabel ? `${baseLabel} — ${entry.sheetLabel}` : baseLabel;
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
        if (entry.cells) {
            // интервал дат записи: пары сетки «разворачиваются» на даты интервала
            const dates = document.createElement('div');
            dates.className = 'entry-dates d-flex flex-wrap align-items-center gap-1 mt-1';
            dates.onclick = e => e.stopPropagation();
            const startLabel = document.createElement('span');
            startLabel.className = 'small text-nowrap';
            startLabel.textContent = 'с';
            const startInput = document.createElement('input');
            startInput.type = 'date';
            startInput.className = 'form-control form-control-sm';
            startInput.value = entry.dateStart || '';
            startInput.title = 'Начальная дата интервала записи';
            startInput.onchange = () => entry.dateStart = startInput.value;
            const endLabel = document.createElement('span');
            endLabel.className = 'small text-nowrap';
            endLabel.textContent = 'по';
            const endInput = document.createElement('input');
            endInput.type = 'date';
            endInput.className = 'form-control form-control-sm';
            endInput.value = entry.dateEnd || '';
            endInput.title = 'Конечная дата интервала записи';
            endInput.onchange = () => entry.dateEnd = endInput.value;
            dates.append(startLabel, startInput, endLabel, endInput);
            item.appendChild(dates);
        }
        const errorText = entry.parseError ||
            (entry.errors && entry.errors._group ? entry.errors._group.join('; ') : null) ||
            (entry.errors ? 'Есть ошибки в ячейках — откройте запись, чтобы увидеть' : null);
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
    const box = document.getElementById('mx-import-cell-errors');
    box.innerHTML = '';
    if (!entry.errors) return;
    const messages = [];
    (entry.errors._group || []).forEach(m => messages.push(m));
    Object.entries(entry.errors).forEach(([key, msgs]) => {
        if (key === '_group') return;
        (msgs || []).forEach(m => messages.push(m));
        const el = document.getElementById(`${key}_discipline`);
        if (el) {
            const row = el.closest('.input-group');
            if (row) row.classList.add('cell-error');
        }
    });
    if (messages.length) {
        box.innerHTML = `<p class="alert alert-danger mb-0" style="white-space: pre-line">${messages.join('\n')}</p>`;
    }
}

function clearCellErrors() {
    document.querySelectorAll('#scheduleForm .cell-error').forEach(el => el.classList.remove('cell-error'));
    document.getElementById('mx-import-cell-errors').innerHTML = '';
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
            body: JSON.stringify({entries: saveable.map(({entry}) => ({
                groups: entry.groups,
                date_start: entry.dateStart || '',
                date_end: entry.dateEnd || '',
                cells: entry.cells
            }))})
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
            document.getElementById('scheduleForm').reset();
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
    const box = document.getElementById('mx-import-summary');
    box.innerHTML = `<p class="alert alert-${type} mt-2 mb-2">${text}</p>`;
}

function showUploadError(text) {
    const el = document.getElementById('mx-import-upload-error');
    el.textContent = text;
    el.style.display = 'block';
}

function hideUploadError() {
    document.getElementById('mx-import-upload-error').style.display = 'none';
}
