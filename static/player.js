document.addEventListener('DOMContentLoaded', () => {

    const sendRequest = async (url, data) => {

        // javascript object -> urlencoded data
        const formData = data
        ? Object.keys(data)
            .map((key) => encodeURIComponent(key) + '=' + encodeURIComponent(data[key]))
            .join('&')
        : null;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });
        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }
        return await response.json();
    };

    const updateSongOnDashboard = (song) => {
        const songInfo = document.getElementById('song-name');
        const playButton = document.getElementById('playButton');

        songInfo.innerText = `${song.title} - ${song.interpret}`;
        playButton.innerText = song.isPlaying ? '⏸' : '▶';
    };

    const playButton = document.getElementById('playButton');
    const backButton = document.getElementById('forwardButton');
    const forwardButton = document.getElementById('backButton');
    const shutdownButton = document.getElementById('shutdownButton');
    const newConnOnButton = document.getElementById('pairing-discoverable-on');
    const newConnOffButton = document.getElementById('pairing-discoverable-off');
    // const playerSlider = document.getElementById('playerSlider');
    // const currentTimeLabel = document.getElementById('song-current');
    // const endTimeLabel = document.getElementById('song-end');
    const volumeSlider = document.getElementById('volumeSlider');

    playButton.addEventListener('click', async () => {
        const res = await sendRequest('/player/play_pause');
        updateSongOnDashboard(res);
    });

    backButton.addEventListener('click', async () => {
        const res = await sendRequest('/player/forward');
        updateSongOnDashboard(res);
    });

    forwardButton.addEventListener('click', async () => {
        const res = await sendRequest('/player/back');
        updateSongOnDashboard(res);
    });

    shutdownButton.addEventListener('click', async () => {
        sendRequest('/shutdown');
    });

    newConnOnButton.addEventListener('click', async () => {
        sendRequest('/bluetooth/discoverable', { status: true });
        sendRequest('/bluetooth/pairable', { status: true });
    });

    newConnOffButton.addEventListener('click', async () => {
        sendRequest('/bluetooth/discoverable', { status: false });
        sendRequest('/bluetooth/pairable', { status: false });
    });

    // playerSlider.addEventListener('change', () => {
    //     sliderChanged = true;
    // });

    // playerSlider.addEventListener('input', () => {
    //     sliderChanged = true;

    //     // calculate length of song in seconds
    //     const minutes = Number.parseInt(endTimeLabel.innerText.split(':')[0])
    //     const seconds = Number.parseInt(endTimeLabel.innerText.split(':')[1])
    //     const songLength = minutes * 60 + seconds // in seconds

    //     // calculate time skipped to
    //     const skippedTo = songLength * playerSlider.value / 100;

    //     const newMinutes = Number.parseInt(skippedTo / 60);
    //     var newSeconds = Number.parseInt(skippedTo % 60);

    //     newSeconds = (newSeconds < 10) ? '0' + newSeconds.toString() : newSeconds.toString();

    //     // update current time on song
    //     currentTimeLabel.innerText = newMinutes + ':' + newSeconds;
    // });

    // playerSlider.addEventListener('mouseup', () => {
    //     if (sliderChanged) {
    //         sendRequest('/player/skip_to', { percentage: playerSlider.value });
    //         sliderChanged = false;
    //     }
    // });

        // playerSlider.addEventListener('change', () => {
    //     sliderChanged = true;
    // });

    volumeSlider.addEventListener('input', () => {
        sliderChanged = true;
    });

    volumeSlider.addEventListener('mouseup', () => {
        if (sliderChanged) {
            sendRequest('/player/volume_to', { percentage: volumeSlider.value / 100 });
            sliderChanged = false;
        }
    });
});
