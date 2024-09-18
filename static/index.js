$(document).ready(function() {

    // --------------------------- ФУНКЦИИ ---------------------------

    // Форматирование даты в формат yyyy-MM-dd
    function formatDate(date) {
        let day = ("0" + date.getDate()).slice(-2);
        let month = ("0" + (date.getMonth() + 1)).slice(-2);
        let year = date.getFullYear();
        return `${year}-${month}-${day}`;
    }

    // Подсказки Дадата
    function initializeSuggestions(selector, type, outputSelector) {
        $(selector).suggestions({
            token: "4eaa705b0abe5c4a4d7f1e28ff2575c61532a8da",
            type: type,
            onSelect: function (suggestion) {
                console.log(suggestion);
                $(outputSelector).val(JSON.stringify(suggestion));
            }
        });
    }

    // Функция для конвертации файла в Base64
    function convertFileToBase64(file) {
        return new Promise((resolve, reject) => {
            var reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    // Загрузка данных из указанного URL
    function loadOptions(url, callback) {
        $.getJSON(url, function(data) {
            var options = data.map(function(item) {
                return '<option value="' + item + '">' + item + '</option>';
            }).join('');
            callback(options);
        });
    }

    // Функция инициализации автозаполнения
    function initializeAutocomplete(selector, url, addFunction) {
        $(selector).autocomplete({
            source: function (request, response) {
                $.getJSON(url, function (data) {
                    console.log('Данные загружены:', data);
                    var results = $.ui.autocomplete.filter(data, request.term);
                    response(results.slice(0, 30));
                });
            },
            minLength: 0,
            select: function (event, ui) {
                console.log('Выбрана позиция:', ui.item.value);
                addFunction(ui.item.value, 1);
                $(selector).val('').autocomplete("close");
                return false;
            }
        }).focus(function () {
            $(this).autocomplete("search", "");
        });
    }

    // Проверка валидности формы
    function checkFormValidity() {
        var isValid = $('#mattressTable .grid-item').length > 0 || $('#additionalTable .grid-item').length > 0;
        $('#submitBtn').prop('disabled', !isValid);
    }

    // Индекс для матрасов
    let mattressIndex = 0;
    // Функция добавления матраса
    function addMattress(mattress, quantity) {
        loadOptions('/api/fabrics', function(fabricOptions) {
            loadOptions('/api/springs', function(springOptions) {
                mattressIndex++; // Увеличиваем индекс при добавлении новой позиции
                var row = '<div class="grid-item" data-type="mattress" data-name="' + mattress + '">' +
                          '<text class="position-label ">' + mattress + '</text>' +
                          '<button type="button" class="btn btn-danger btn-sm remove-item">Удалить</button>' +
                          '<div class="form-row">' +
                          '<div class="col">' +
                          '<label for="quantity_mattress_' + mattressIndex + '">Количество</label>' +
                          '<input type="number" value="1" id="quantity_mattress_' + mattressIndex + '" name="quantity_mattress[' + mattressIndex + ']" class="form-control">' +
                          '</div>' +
                          '<div class="col">' +
                          '<label for="price_mattress_' + mattressIndex + '">Цена</label>' +
                          '<input type="number" id="price_mattress_' + mattressIndex + '" name="price_mattress[' + mattressIndex + ']" class="form-control">' +
                          '</div>' +
                          '<div class="col">' +
                          '<label for="size_mattress_' + mattressIndex + '">Размер</label>' +
                          '<input type="text" id="size_mattress_' + mattressIndex + '" name="size_mattress[' + mattressIndex + ']" class="form-control">' +
                          '</div>' +
                          '</div>' +
                          '<label for="top_fabric_mattress_' + mattressIndex + '" class="mattress-option-label">Ткань - топ</label>' +
                          '<select id="top_fabric_mattress_' + mattressIndex + '" name="top_fabric_mattress[' + mattressIndex + ']" class="form-control">' + fabricOptions + '</select>' +
                          '<label for="side_fabric_mattress_' + mattressIndex + '" class="mattress-option-label">Ткань - бок</label>' +
                          '<select id="side_fabric_mattress_' + mattressIndex + '" name="side_fabric_mattress[' + mattressIndex + ']" class="form-control">' + fabricOptions + '</select>' +
                          '<label for="spring_block_mattress_' + mattressIndex + '" class="mattress-option-label">Пружинный блок</label>' +
                          '<select id="spring_block_mattress_' + mattressIndex + '" name="spring_block_mattress[' + mattressIndex + ']" class="form-control">' + springOptions + '</select>' +
                          '<label for="photo_mattress_' + mattressIndex + '" class="mattress-option-label">Фото</label>' +
                          '<input type="file" id="photo_mattress_' + mattressIndex + '" name="photo_mattress[' + mattressIndex + ']" class="form-control file-field">' +
                          '<input type="text" id="comment_mattress_' + mattressIndex + '" name="comment_mattress[' + mattressIndex + ']" placeholder="Комментарий" class="form-control">' +
                          '</div>';
                $('#mattressTable').append(row);
                checkFormValidity();
            });
        });
    }

    // Индекс для дополнительных позиций
    let additionalIndex = 0;
    // Функция добавления допника
    function addAdditional(item, quantity) {
            additionalIndex++; // Увеличиваем индекс при добавлении новой позиции
            var row = '<div class="grid-item" data-type="additional" data-name="' + item + '">' +
                      '<text class="position-label">' + item + '</text>' +
                      '<button type="button" class="btn btn-danger btn-sm remove-item">Удалить</button>' +
                      '<div class="form-row">' +
                      '<div class="col">' +
                      '<label for="quantity_additional_' + additionalIndex + '">Количество</label>' +
                      '<input type="number" value="1" id="quantity_additional_' + additionalIndex + '" name="quantity_additional[' + additionalIndex + ']" class="form-control">' +
                      '</div>' +
                      '<div class="col">' +
                      '<label for="price_additional_' + additionalIndex + '">Цена</label>' +
                      '<input type="number" id="price_additional_' + additionalIndex + '" name="price_additional[' + additionalIndex + ']" class="form-control">' +
                      '</div>' +
                      '</div>';
            $('#additionalTable').append(row);
            checkFormValidity();
    }

    // Сбор данных из формы в виде JSON
    function collectFormData() {
        var data = {
            mattresses: [],
            additionalItems: [],
            deliveryDate: $('#delivery_date').val(),
            prepayment: $('input[name="prepayment"]').val(),
            organization: $('input[name="organization"]').val(),
            contact: $('input[name="contact"]').val(),
            deliveryType: $('select[name="delivery_type"]').val(),
            deliveryAddress: $('input[name="delivery_address"]').val(),
            regionSelect: $('select[name="region_select"]').val()
        };

        // Собираем данные для матрасов
         $('#mattressTable .grid-item').each(async function() {
            let $element = $(this);

            let photoFile = $element.find('input[name^="photo_mattress"]').prop('files')[0];
            let photoBase64 = '';
            if (photoFile) {
                photoBase64 = await convertFileToBase64(photoFile);
            }

            var item = {
                name: $element.data('name'),
                quantity: $element.find('input[name^="quantity_mattress"]').val(),
                price: $element.find('input[name^="price_mattress"]').val(),
                size: $element.find('input[name^="size_mattress"]').val(),
                topFabric: $element.find('select[name^="top_fabric_mattress"]').val(),
                sideFabric: $element.find('select[name^="side_fabric_mattress"]').val(),
                springBlock: $element.find('select[name^="spring_block_mattress"]').val(),
                comment: $element.find('input[name^="comment_mattress"]').val(),
                photo: photoBase64
            };

            data.mattresses.push(item);
        });

        // А тут собираются дополнительные позиции
        $('#additionalTable .grid-item').each(function() {
            let $element = $(this);

            var item = {
                name: $element.data('name'),
                quantity: $element.find('input[name^="quantity_additional"]').val(),
                price: $element.find('input[name^="price_additional"]').val()
            };

            data.additionalItems.push(item);
        });

        // Возвращаем объект с данными
        return data;
    }

    // --------------------------- ОБРАБОТЧИКИ ---------------------------

    $('#delivery_address').change(function () {
        $('#address_data').val($(this).val());
    });

    // Обработчик событий для кнопок удаления
    $(document).on('click', '.remove-item', function() {
        $(this).closest('.grid-item').remove();
        checkFormValidity();
    });

    // Обработка изменения типа доставки
    $('select[name="delivery_type"]').change(function() {
        var deliveryType = $(this).val();
        $('#address-group').toggle(deliveryType !== 'Самовывоз');
        $('#region-group').toggle(deliveryType === 'Регионы');
    });

    // Поведение при отправке формы. Кнопка становится неактивной при нажатии, чтобы юзверь не успел несколько раз создать реализацию
    $('form').on('submit', function (event) {
        // Останавливаем стандартное поведение формы
        event.preventDefault();
        // Собираем данные в JSON
        let form = $(this);
        let formData = collectFormData();
        // Делаем кнопку неактивной и меняем текст
        var submitBtn = $('#submitBtn');
        submitBtn.prop('disabled', true).text('Отправка...');

        $.ajax({
            url: form.attr('action'),
            type: form.attr('method'),
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function (response) {
                if (response.includes("Заявка принята")) {
                    alert(response.trim()); // Показываем сообщение с результатом
                    window.location.reload(); // Перезагружаем страницу
                } else {
                    // Одна ошибка и ты ошибся... Активируем кнопку снова при ошибке
                    console.error('Ошибка обработки формы', response);
                    alert("Что-то пошло не так. Пожалуйста, попробуйте еще раз.");
                    submitBtn.prop('disabled', false).text('Создать реализацию');
                }
            },
            // Одна ошибка и ты ошибся... Активируем кнопку снова при ошибке
            error: function (error) {
                console.error('Ошибка отправки формы', error);
                alert("Ошибка при отправке формы.");
                submitBtn.prop('disabled', false).text('Создать реализацию');
            }
        });
    });

    // --------------------------- ИНИЦИАЦИЯ ---------------------------

    // Инициализация автозаполнения для матрасов и допов
    initializeAutocomplete('#mattressArticle', '/api/mattresses', addMattress);
    initializeAutocomplete('#additionalArticle', '/api/nomenclatures', addAdditional);
    // Установка сегодняшней даты в поле
    $('#delivery_date').val(formatDate(new Date()));

    // Инициализация подсказок для адреса и компаний
    initializeSuggestions("#organization", "PARTY", "#organization_data");
    initializeSuggestions("#delivery_address", "ADDRESS", "#address_data");
});
