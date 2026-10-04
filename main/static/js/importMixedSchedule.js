async function importSchedule() {
    const fileInput = document.getElementById("ScheduleFile");
    selectedFile = fileInput.files[0];
    const formData = new FormData();
    formData.append("excel_table", selectedFile);
    formData.append("education_form", "full_time");
    formData.append("education_type", "higher_education");

    try {
        const response = await fetch("http://tfcsu.ru:8001/schedule/parser/schedule/parse", {
            method: "POST",
            body: formData,
        });
        const result = await response.json();
        if (response.ok) {
            parseResult(result);
            document.getElementById("ft-import-upload-error").style.display = 'none';
        } else {
            console.log("Upload failed:", result.details);
            document.getElementById("ft-import-upload-error").innerHTML = result.details;
            document.getElementById("ft-import-upload-error").style.display = 'block';
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
  const weekDays = {
        "понедельник": "пн",
        "вторник": "вт",
        "среда": "ср",
        "четверг": "чт",
        "пятница": "пт",
        "суббота": "сб",
        "воскресенье": "вс"
    }
    const weekNumbers = {
        "first_week": 1,
        "second_week": 2
    }

    document.getElementById('scheduleForm').reset();
    for (const week_key in schedule) {
      const weekNumber = weekNumbers[week_key];
      for (const day_key in schedule[week_key]) {
        const shortDay = weekDays[day_key];
        schedule[week_key][day_key].forEach((lesson, index) => {
            document.getElementById(`${weekNumber}_${shortDay}_${lesson.number}_is_special`).checked = lesson.is_special
            document.getElementById(`${weekNumber}_${shortDay}_${lesson.number}_discipline`).value = lesson.discipline_title;
            document.getElementById(`${weekNumber}_${shortDay}_${lesson.number}_format`).value = lesson.format;
            document.getElementById(`${weekNumber}_${shortDay}_${lesson.number}_teacher`).value = lesson.teacher_name;
            document.getElementById(`${weekNumber}_${shortDay}_${lesson.number}_auditorium`).value = lesson.auditorium_number;
        });
      }
    }
}

document.addEventListener("DOMContentLoaded", function() {
  const selectElement = document.getElementById("importGroups");
  selectElement.addEventListener("change", handleGroupSelectChange);
});

function handleGroupSelectChange() {
  const selectElement = document.getElementById("importGroups");
  const optionSchedule = selectElement.value;
  const optionGroup = selectElement.options[selectElement.selectedIndex].text;
  parseSchedule(JSON.parse(optionSchedule), optionGroup);
  }
