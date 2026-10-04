async function importPartTimeSchedule() {
    const fileInput = document.getElementById("ScheduleFile");
    selectedFile = fileInput.files[0];
    const formData = new FormData();
    formData.append("excel_table", selectedFile);
    formData.append("education_form", "part_time");
    formData.append("education_type", "higher_education");

    try {
        const response = await fetch("http://tfcsu.ru:8001/schedule/parser/schedule/parse", {
            method: "POST",
            body: formData,
        });
        const result = await response.json();
        if (response.ok) {
            parseResult(result);
            document.getElementById("pt-import-upload-error").style.display = 'none';
        } else {
            console.log("Upload failed:", result.details);
            document.getElementById("pt-import-upload-error").innerHTML = result.details;
            document.getElementById("pt-import-upload-error").style.display = 'block';
        }
    } catch (error) {
        console.error("Error during upload:", error);
    }

}

function parseResult(result) {
    const selectElement = document.getElementById('importGroup');
    selectElement.innerHTML = result.results[0].groups[0]
    document.getElementById("hiddenImportGroup").value = selectElement.innerHTML;
    parseSchedule(result.results[0].schedule);

}


function parseSchedule(schedule) {
    const container = document.getElementById("schedule-container");
    container.innerHTML = '';
    for (const day_key in schedule) {
        schedule[day_key].forEach((lesson, index) => {
        const HTML = `
        <div class="input-group">
            <span class="input-group-text" style="min-width:100px">${day_key}</span>
            <span class="input-group-text">${lesson.number}</span>
            <div class="input-group-text">
                <input name="${day_key}_${lesson.number}_is_special"
                       type="checkbox" class="form-check-input mt-0"
                       ${lesson.is_special ? "checked" : ""}>
            </div>
            <textarea name="${day_key}_${lesson.number}_discipline" class="form-control" rows="1">${lesson.discipline_title}</textarea>
            <input name="${day_key}_${lesson.number}_format" type="text" class="form-control" style="max-width:250px" value="${lesson.format}">
            <input name="${day_key}_${lesson.number}_teacher" type="text" class="form-control" style="max-width:200px" value="${lesson.teacher_name}">
            <input name="${day_key}_${lesson.number}_auditorium" type="text" class="form-control" style="max-width:60px" value="${lesson.auditorium_number}">
        </div>
        `;
        container.insertAdjacentHTML('beforeend', HTML);
        });
      }
    }
