document.addEventListener('DOMContentLoaded', () => {

    const sendRequest = (url, data) => {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', url, true);
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        xhr.onreadystatechange = () => {
            if (xhr.readyState === 4 && xhr.status === 200) {
                // Handle success response from the server
            }
        };
        var formData = data ? Object.keys(data).map(function(key) {
            return encodeURIComponent(key) + '=' + encodeURIComponent(data[key]);
        }).join('&') : null;
        xhr.send(formData);
    };

    var playButton = document.getElementById('playButton');
    var backButton = document.getElementById('forwardButton');
    var forwardButton = document.getElementById('backButton');
    var playerSlider = document.getElementById('playerSlider');
    var currentTimeLabel = document.getElementById('song-current');
    var endTimeLabel = document.getElementById('song-end');

    playButton.addEventListener('click', () => {
        sendRequest('/player/play_pause');
    });

    backButton.addEventListener('click', () => {
        sendRequest('/player/forward');
    });

    forwardButton.addEventListener('click', () => {
        sendRequest('/player/back');
    });

    playerSlider.addEventListener('change', () => {
        sliderChanged = true;
    });

    playerSlider.addEventListener('input', () => {
        sliderChanged = true;

        // calculate length of song in seconds
        const minutes = Number.parseInt(endTimeLabel.innerText.split(':')[0])
        const seconds = Number.parseInt(endTimeLabel.innerText.split(':')[1])
        const songLength = minutes * 60 + seconds // in seconds

        // calculate time skipped to
        const skippedTo = songLength * playerSlider.value / 100;

        const newMinutes = Number.parseInt(skippedTo / 60);
        var newSeconds = Number.parseInt(skippedTo % 60);

        newSeconds = (newSeconds < 10) ? '0' + newSeconds.toString() : newSeconds.toString();

        // update current time on song
        currentTimeLabel.innerText = newMinutes + ':' + newSeconds;
    });

    playerSlider.addEventListener('mouseup', () => {
        if (sliderChanged) {
            sendRequest('/player/skip_to', { percentage: playerSlider.value });
            sliderChanged = false;
        }
    });
});
