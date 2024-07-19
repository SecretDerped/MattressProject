document.addEventListener('DOMContentLoaded', function () {
    let capturing = false;
    let currentEmployeeSequence = '';

    document.addEventListener('keydown', function (event) {
        let key = event.key;

        if (key === '(') {
            capturing = true;
            currentEmployeeSequence = '';
            sendKey(key);
        } else if (key === ')') {
            capturing = false;
            sendKey(key);
        } else if (capturing) {
            currentEmployeeSequence += key;
            sendKey(key);
        }
    });

    function sendKey(key) {
        fetch('/log_sequence_gluing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ key: key })
        })
        .then(response => response.json())
        .then(data => {
            if (data.sequence) {
                console.log(`Считанная последовательность: ${data.sequence}`);
                document.getElementById('message').innerText = `Сотрудник: ${data.sequence}`;
            }
            if (data.task_data) {
                let firstRecordHtml = Object.entries(data.task_data)
                    .map(([key, value]) => `<div>${key}: ${value}</div>`)
                    .join('');
                document.getElementById('task_data').innerHTML = firstRecordHtml;
                document.getElementById('buttons').style.display = 'block';
                document.getElementById('complete_button').dataset.taskId = data.task_data.id; // Используем идентификатор задачи
                document.getElementById('complete_button').dataset.employeeSequence = currentEmployeeSequence;
            }
        });
    }

    document.getElementById('hide_button').addEventListener('click', function () {
        document.getElementById('message').innerText = 'Жду штрих-код...';
        document.getElementById('task_data').innerHTML = 'Данные первой записи будут отображаться здесь.';
        document.getElementById('buttons').style.display = 'none';
    });

    document.getElementById('complete_button').addEventListener('click', function () {
        let taskId = this.dataset.taskId;
        let employeeSequence = this.dataset.employeeSequence;

        fetch('/complete_task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ task_id: taskId, employee_sequence: employeeSequence })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // Симуляция ввода закрывающей скобки
                sendKey(')');
            }
        });
    });
});
