document.addEventListener('DOMContentLoaded', function () {
    let capturing = false;
    let currentEmployeeSequence = '';

    document.addEventListener('keydown', function (event) {
        let key = event.key;

        if (key === '(') {
            capturing = true;
            currentEmployeeSequence = '';
            sendKey(key, '/log_sequence_sewing'); // Меняем на '/log_sequence_sewing' для страницы сшивания
        } else if (key === ')') {
            capturing = false;
            sendKey(key, '/log_sequence_sewing'); // Меняем на '/log_sequence_sewing' для страницы сшивания
        } else if (capturing) {
            currentEmployeeSequence += key;
            sendKey(key, '/log_sequence_sewing'); // Меняем на '/log_sequence_sewing' для страницы сшивания
        }
    });

    function sendKey(key, url) {
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ key: key })
        })
        .then(response => response.json())
        .then(data => {
            console.log(data); // Логирование ответа сервера
            if (data.sequence) {
                console.log(`Считанная последовательность: ${data.sequence}`);
                document.getElementById('message').innerText = `👷‍♂️ ${data.sequence}`;
            }
            if (data.task_data) {
                if (data.task_data.error) {
                    document.getElementById('task_data').innerText = data.task_data.error;
                } else {
                    displayTaskData(data.task_data);
                    document.getElementById('buttons').style.display = 'block';
                    document.getElementById('complete_button').dataset.employeeSequence = currentEmployeeSequence;
                }
            }
        })
        .catch(error => {
            console.error('Ошибка при отправке запроса:', error);
        });
    }

    document.getElementById('hide_button').addEventListener('click', function () {
        resetPage();
    });

    document.getElementById('complete_button').addEventListener('click', function () {
        let employeeSequence = this.dataset.employeeSequence;

        console.log(`Завершение задачи для сотрудника: ${employeeSequence}`); // Логирование перед отправкой запроса

        fetch('/complete_task_sewing', { // Меняем на '/complete_task_sewing' для страницы сшивания
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ employee_sequence: employeeSequence })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // Возвращаем страницу в начальное состояние
                resetPage();
            } else {
                console.error('Ошибка при завершении задачи:', data.message);
            }
        })
        .catch(error => {
            console.error('Ошибка при завершении задачи:', error);
        });
    });

    function resetPage() {
        document.getElementById('message').innerText = '';
        document.getElementById('task_data').innerHTML = 'Жду штрих-код...';
        document.getElementById('buttons').style.display = 'none';
    }

        function displayTaskData(taskData) {
        var taskContainer = document.getElementById('task_data');
        taskContainer.innerHTML = ''; // Очищаем контейнер перед заполнением

        // Добавляем основные данные
        for (var key in taskData) {
            if (key !== 'Фото' && taskData[key]) {
                taskContainer.innerHTML += `<p><strong>${key}:</strong> ${taskData[key]}</p>`;
            }
        }

        // Если есть фото, добавляем его в конец
        if (taskData['Фото']) {
            var imgElement = document.createElement('img');
            imgElement.src = taskData['Фото'];
            imgElement.alt = 'Фото';
            imgElement.classList.add('thumbnail');

            // Добавляем обработчик клика
            imgElement.addEventListener('click', function () {
                imgElement.classList.toggle('expanded');
            });

            taskContainer.appendChild(imgElement);
        }
    }
});
