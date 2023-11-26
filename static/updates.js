const setGaugeValue = (gauge, percentage, value, unit) => {

    if (percentage < 0 || percentage > 1) return;
    
    gauge.querySelector(".gauge__fill").style.transform = `rotate(${ percentage / 2 }turn)`;
    gauge.querySelector(".gauge__cover").textContent = value + " " + unit;
};

const socket = io.connect('http://' + document.domain + ':' + location.port);
const rpmGauge = document.querySelector(".rpm-gauge");
const kmhGauge = document.querySelector(".kmh-gauge");

socket.on('dashboard_update', (message) => {

    const data = JSON.parse(message);

    const kmhPercentage = Number.parseInt(data.kmh) / 200;
    const rpmPercentage = Number.parseInt(data.rpm) / 6000;

    setGaugeValue(rpmGauge, rpmPercentage, data.rpm, "rpm");
    setGaugeValue(kmhGauge, kmhPercentage, data.kmh, "kmh");
});

var playButton = document.getElementById('playButton');
var songNameLabel = document.getElementById('song-name');
// var songEndLabel = document.getElementById('song-end');

socket.on('player_update', (message) => {

    const data = JSON.parse(message);

    songNameLabel.innerText = data.song.interpret + ' - ' + data.song.titel;

    playButton.innerText = '⏸' ? data.isPlaying : '▶'

	// const newMinutes = Number.parseInt(data.song.length / 60);
	// var newSeconds = Number.parseInt(data.song.length % 60);

 	// newSeconds = (newSeconds < 10) ? '0' + newSeconds.toString() : newSeconds.toString();

	// songEndLabel.innerText = newMinutes + ':' + newSeconds;
})
