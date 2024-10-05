document.addEventListener('DOMContentLoaded', function () {
    let capturing = false;
    let currentEmployeeSequence = '';

    document.addEventListener('keydown', function (event) {
        // Игнорируем нажатия клавиш-модификаторов
        if (event.key === 'Shift' || event.key === 'Control' || event.key === 'Alt') {
            return;
        }

        let key = event.key;

        if (key === '(') {
            capturing = true;
            currentEmployeeSequence = '';
            console.log('Начало считывания последовательности...');
        } else if (key === ')') {
            capturing = false;
            console.log('Конец считывания. Полученная последовательность:', currentEmployeeSequence);
            processSequence(currentEmployeeSequence);  // Отправляем всю последовательность на сервер
        } else if (capturing) {
            currentEmployeeSequence += key;
        }
    });

    function processSequence(sequence) {
        console.log('Отправка последовательности на сервер:', sequence);

        fetch('/log_sequence_sewing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ sequence: sequence })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Ответ от сервера:', data); // Логирование ответа сервера
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
            console.error('Ошибка при отправке последовательности:', error);
        });
    }

    document.getElementById('hide_button').addEventListener('click', function () {
        resetPage();
    });

    document.getElementById('complete_button').addEventListener('click', function () {
        let employeeSequence = this.dataset.employeeSequence;

        console.log(`Завершение задачи для сотрудника: ${employeeSequence}`); // Логирование перед отправкой запроса

        fetch('/complete_task_sewing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ employee_sequence: employeeSequence })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Возвращаем страницу в начальное состояние
                resetPage();
            } else {
                console.error('Ошибка при завершении задачи:', data.message);
                document.getElementById('task_data').innerText = 'Ошибка при завершении задачи.';
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
