document.addEventListener('DOMContentLoaded', () => {

    const sendRequest = (url, data) => {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', url, true);
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        xhr.onreadystatechange = () => {
            if (xhr.readyState === 4 && xhr.status === 200) {
                try {
                    return JSON.parse(xhr.responseText);
                }
                catch(error) {
                    // handle error
                    console.log(error);
                }
            }
        };
        var formData = data ? Object.keys(data).map(function(key) {
            return encodeURIComponent(key) + '=' + encodeURIComponent(data[key]);
        }).join('&') : null;
        xhr.send(formData);
    };

    const updateSongOnDashboard = (song) => {
        const songInfo = document.getElementById('song-info');
        const playButton = document.getElementById('play-button');

        songInfo.innerText = `${song.titel} - ${song.interpet}`;
        playButton.innerText = song.isPlaying ? '⏸' : '▶';
    };

    const playButton = document.getElementById('playButton');
    const backButton = document.getElementById('forwardButton');
    const forwardButton = document.getElementById('backButton');
    const playerSlider = document.getElementById('playerSlider');
    const currentTimeLabel = document.getElementById('song-current');
    const endTimeLabel = document.getElementById('song-end');

    playButton.addEventListener('click', () => {
        const res = sendRequest('/player/play_pause');
        updateSongOnDashboard(res);
    });

    backButton.addEventListener('click', () => {
        const res = sendRequest('/player/forward');
        updateSongOnDashboard(res);
    });

    forwardButton.addEventListener('click', () => {
        const res = sendRequest('/player/back');
        updateSongOnDashboard(res);
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
