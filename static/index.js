console.log("index.js загружен и выполняется");

document.querySelector('.file-input').addEventListener('change', function(event) {
    var file = event.target.files[0];
    var fileName = file ? file.name : '📁 Прикрепить файл ☁️';
    var fileError = document.getElementById('file-error');
    fileError.style.display = 'none';

    if (file && file.size <= 20 * 1024 * 1024 && (file.type === 'image/jpeg' || file.type === 'image/png')) {
        updateFileButton(fileName, 'btn-primary', 'btn-danger');
    } else {
        updateFileButton('📁 Прикрепить файл ☁️', 'btn-danger', 'btn-primary');
        fileError.style.display = 'block';
        event.target.value = '';
    }
});

function updateFileButton(text, addClass, removeClass) {
    var button = document.querySelector('.custom-file-input-button');
    button.textContent = text;
    button.classList.add(addClass);
    button.classList.remove(removeClass);
}

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

initializeSuggestions("#party", "PARTY", "#party_data");
initializeSuggestions("#delivery_address", "ADDRESS", "#address_data");

$('#delivery_address').change(function () {
    $('#address_data').val($(this).val());
});

$('input[name="delivery_type"]').change(function () {
    var selectedType = $('input[name="delivery_type"]:checked').val();
    toggleAddressFields(selectedType);
});

function toggleAddressFields(selectedType) {
    if (selectedType === 'Самовывоз') {
        $('#address-group').hide();
        $('#region-group').hide();
    } else if (selectedType === 'Город' || selectedType === 'Край') {
        $('#address-group').show();
        $('#region-group').hide();
    } else if (selectedType === 'Регионы' || selectedType === 'Страны') {
        $('#address-group').show();
        $('#region-group').show();
    }
}

$("#photo").change(function () {
    var file = this.files[0];
    if (file) {
        var reader = new FileReader();
        reader.onload = function (e) {
            $('#photo_data').val(e.target.result);
        };
        reader.readAsDataURL(file);
    }
});

$(document).ready(function () {
    setInitialDateAndRegion();
    initializeAutocomplete("#base_fabric", '/api/fabrics');
    initializeAutocomplete("#side_fabric", '/api/fabrics');
    initializeAutocomplete("#springs", '/api/springs');
    initializePositionsAutocomplete();
});

$(document).ready(function () {
    // Скролл к инпуту при фокусе на нем
    $('input[type="text"], textarea').focus(function () {
        // Определение текущего элемента
        var inputField = $(this);

        // Небольшая задержка, чтобы клавиатура успела появиться
        setTimeout(function () {
            var elementTop = inputField.offset().top;
            $('html, body').animate({
                scrollTop: elementTop - 20 // Смещение на 20px выше
            }, 300); // Анимация скролла на 300 мс
        }, 250);
    });
});

function setInitialDateAndRegion() {
    var today = new Date();
    var dd = String(today.getDate()).padStart(2, '0');
    var mm = String(today.getMonth() + 1).padStart(2, '0');
    var yyyy = today.getFullYear();
    var formattedDate = yyyy + '-' + mm + '-' + dd;
    $('#delivery_date').val(formattedDate);
    $('#region_select option:first').prop('selected', true);
}

function initializePositionsAutocomplete() {
    var positions = [];
    $('#positionsTable').hide();

    function checkPositions() {
        if (positions.length > 0) {
            $('#submitBtn').prop('disabled', false);
        } else {
            $('#submitBtn').prop('disabled', true);
        }
    }

    function updatePositionsInput() {
        $('#positionsData').val(JSON.stringify(positions));
        checkPositions();
    }

    function addPosition(article, quantity) {
        var existingPosition = positions.find(position => position.article === article);
        if (existingPosition) {
            existingPosition.quantity += quantity;
        } else {
            positions.push({ article: article, quantity: quantity, price: 0 });
        }
        updatePositionsTable();
        updatePositionsInput();
        toggleUniqueMattressSize();
    }

    function updatePositionsTable() {
        var tableBody = $('#positionsTable tbody');
        tableBody.empty();
        positions.forEach(function (position, index) {
            var row = $('<tr></tr>');
            row.append($('<td></td>').text(position.article));

            var quantityCell = $('<td class="quantity-col"></td>');
            var minusButton = $('<button type="button" class="btn btn-secondary btn-sm mx-1">-</button>').click(function () {
                updateQuantity(index, -1);
            });
            var quantityInput = $('<span class="quantity">' + position.quantity + '</span>').on('input', function () {
                updateQuantity(index, parseInt($(this).text(), 10));
            });
            var plusButton = $('<button type="button" class="btn btn-secondary btn-sm mx-1">+</button>').click(function () {
                updateQuantity(index, 1);
            });
            quantityCell.append(minusButton, quantityInput, plusButton);
            row.append(quantityCell);

            // Новая колонка для цены
            var priceCell = $('<td></td>');
            var priceInput = $('<input type="number" class="form-control price-input" min="0" step="0.01" placeholder="Цена">')
                .val(position.price)
                .on('input', function () {
                    updatePrice(index, parseFloat($(this).val()));
                });
            priceCell.append(priceInput);
            row.append(priceCell);

            tableBody.append(row);
        });

        $('#positionsTable').toggle(positions.length > 0);
    }

    function updateQuantity(index, delta) {
        var quantity = positions[index].quantity + delta;
        if (quantity > 0 && quantity <= 999) {
            positions[index].quantity = quantity;
            updatePositionsTable();
            updatePositionsInput();
        } else if (quantity <= 0) {
            positions.splice(index, 1);
            updatePositionsTable();
            updatePositionsInput();
        }
        toggleUniqueMattressSize();
    }

    function updatePrice(index, price) {
        if (!isNaN(price)) {
            positions[index].price = price;
            updatePositionsInput();
        }
    }

    function toggleUniqueMattressSize() {
        var uniqueMattress = positions.some(position => position.article === 'Уникальный матрас');
        if (uniqueMattress) {
            $('#uniqueMattressSize').show();
        } else {
            $('#uniqueMattressSize').hide();
        }
    }

    $('#newArticle').autocomplete({
        source: function (request, response) {
            $.getJSON('/api/nomenclatures', function (data) {
                var results = $.ui.autocomplete.filter(data, request.term);
                response(results.slice(0, 30)); // Ограничиваем количество результатов до 30
            });
        },
        minLength: 0,
        select: function (event, ui) {
            addPosition(ui.item.value, 1);
            $('#newArticle').val('').autocomplete("close");
            return false;
        }
    }).focus(function () {
        $(this).autocomplete("search", "");
    });
}

function initializeAutocomplete(selector, apiUrl) {
    $(selector).autocomplete({
        source: function (request, response) {
            $.getJSON(apiUrl, function (data) {
                var results = $.ui.autocomplete.filter(data, request.term);
                response(results.slice(0, 50)); // Ограничиваем количество результатов до 30
            });
        },
        minLength: 0,
        select: function (event, ui) {
            $(selector).val(ui.item.value).autocomplete("close");
            return false;
        },
    }).focus(function () {
        $(this).autocomplete("search", "");
    });
}

$(document).ready(function () {
    $('form').on('submit', function (event) {
        event.preventDefault(); // Останавливаем стандартное поведение формы

        var form = $(this);

        $.ajax({
            type: form.attr('method'),
            url: form.attr('action'),
            data: form.serialize(),
            success: function (response) {
                if (response.includes("Заявка принята")) {
                    alert(response.trim()); // Показываем сообщение с результатом
                    window.location.reload(); // Перезагружаем страницу
                } else {
                    alert("Что-то пошло не так. Пожалуйста, попробуйте еще раз.");
                }
            },
            error: function () {
                alert("Ошибка при отправке формы. Пожалуйста, попробуйте еще раз.");
            }
        });
    });
});