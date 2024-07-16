document.addEventListener('DOMContentLoaded', function () {
    let capturing = false;

    document.addEventListener('keydown', function (event) {
        let key = event.key;

        if (key === '(') {
            capturing = true;
            sendKey(key);
        } else if (key === ')') {
            capturing = false;
            sendKey(key);
        } else if (capturing) {
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
                document.getElementById('message').innerText = `${data.sequence}`;
            }
        });
    }
});
