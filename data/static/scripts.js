const up_arrow = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M233.4 105.4c12.5-12.5 32.8-12.5 45.3 0l192 192c12.5 12.5 12.5 32.8 0 45.3s-32.8 12.5-45.3 0L256 173.3 86.6 342.6c-12.5 12.5-32.8 12.5-45.3 0s-12.5-32.8 0-45.3l192-192z"/>
    <title>{TITLE}</title>
</svg>
`;
const high_arrow = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M246.6 41.4c-12.5-12.5-32.8-12.5-45.3 0l-160 160c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L224 109.3 361.4 246.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-160-160zm160 352l-160-160c-12.5-12.5-32.8-12.5-45.3 0l-160 160c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L224 301.3 361.4 438.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3z"/>
    <title>{TITLE}</title>
</svg>
`;
const down_arrow = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M233.4 406.6c12.5 12.5 32.8 12.5 45.3 0l192-192c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L256 338.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l192 192z"/>
    <title>{TITLE}</title>
</svg>
`;
const low_arrow = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M246.6 470.6c-12.5 12.5-32.8 12.5-45.3 0l-160-160c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0L224 402.7 361.4 265.4c12.5-12.5 32.8-12.5 45.3 0s12.5 32.8 0 45.3l-160 160zm160-352l-160 160c-12.5 12.5-32.8 12.5-45.3 0l-160-160c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0L224 210.7 361.4 73.4c12.5-12.5 32.8-12.5 45.3 0s12.5 32.8 0 45.3z"/>
    <title>{TITLE}</title>
</svg>
`;
const stagnating = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M432 256c0 17.7-14.3 32-32 32L48 288c-17.7 0-32-14.3-32-32s14.3-32 32-32l352 0c17.7 0 32 14.3 32 32z"/>
    <title>{TITLE}</title>
</svg>
`;
window.onload = function() {
    fetch('/get?history')
        .then(response => response.json())
        .then(data => {
            data.items.forEach(item => {
                weatherHistoryData.push(item);
            });
            refferenceData = data.refference;
            updateHistory();
        })
        .catch(error => console.log('Error fetching historycal weather:', error));

    // Simulated weather history data
    let weatherHistoryData = [];
    let refferenceData = null;
    
    let createItem = function(item, prevItem) {
        const weatherItemDiv = document.createElement('div');
        weatherItemDiv.classList.add('weatherItem');
        let pressure_dif = (Math.round((((prevItem.pressure / 100) + Number.EPSILON) * 10) / 10)) - (Math.round((((item.pressure / 100) + Number.EPSILON) * 10) / 10));
        let humidity_dif = prevItem.humidity - item.humidity;
        let temperature_dif = prevItem.temperature - item.temperature;
        let heatindex_dif = prevItem.heatindex - item.heatindex;
        let pressure_arrow = pressure_dif < -0.5 ? high_arrow : pressure_dif < 0 ? up_arrow : pressure_dif > 0.5 ? low_arrow : pressure_dif > 0 ? down_arrow : stagnating;
        let humidity_arrow = humidity_dif < -0.5 ? high_arrow : humidity_dif < 0 ? up_arrow : humidity_dif > 0.5 ? low_arrow : humidity_dif > 0 ? down_arrow : stagnating;
        let temperature_arrow = temperature_dif < -1 ? high_arrow : temperature_dif < 0 ? up_arrow : temperature_dif > 1 ? low_arrow : temperature_dif > 0 ? down_arrow : stagnating;
        let heatindex_arrow = heatindex_dif < -1 ? high_arrow : heatindex_dif < 0 ? up_arrow : heatindex_dif > 1 ? low_arrow : heatindex_dif > 0 ? down_arrow : stagnating;
        let pressure_color = pressure_dif > 0 ? "red" : pressure_dif < 0 ? "cyan" : "white"
        let humidity_color = humidity_dif > 0 ? "red" : humidity_dif < 0 ? "cyan" : "white"
        let temperature_color = temperature_dif > 0 ? "red" : temperature_dif < 0 ? "cyan" : "white"
        let heatindex_color = heatindex_dif > 0 ? "red" : heatindex_dif < 0 ? "cyan" : "white"
        weatherItemDiv.innerHTML = `
            <div class="time">
                <span>${item.time}</span>
            </div>
            <div class="temp" style="--color: hsl(${item.temperature_color}, 100%, 50%);--icon-color: ${temperature_color}">
                <span>${item.temperature} ${item.temperature_unit} ${temperature_arrow.replace("{TITLE}", temperature_dif)}</span>
            </div>
            <div class="humidity" style="--color: ${humidity_color};--icon-color: var(--color)">
                <span>${item.humidity} % ${humidity_arrow.replace("{TITLE}", humidity_dif)}</span>
            </div>
            <div class="temp" style="--color: hsl(${item.heatindex_color}, 100%, 50%);--icon-color: ${heatindex_color}">
                <span>${item.heatindex} ${item.temperature_unit} ${heatindex_arrow.replace("{TITLE}", heatindex_dif)}</span>
            </div>
            <div class="pressure" style="--color: ${pressure_color};--icon-color: var(--color)">
                <span>${Math.round(((item.pressure / 100) + Number.EPSILON) * 10) / 10} mbar ${pressure_arrow.replace("{TITLE}", pressure_dif)}</span>
            </div>
        `;
        return weatherItemDiv;
    }

    let updateHistory = function() {
        const weatherHistoryDiv = document.getElementById('weatherHistory');
        let prevItem = refferenceData;
        let temp = [];
        weatherHistoryData.slice().reverse().forEach(item => {
            temp.push(createItem(item, prevItem));
            prevItem = item;
        });
        //temp.push(createItem(refferenceData, prevItem));
        temp.slice().reverse().forEach(item => {
            weatherHistoryDiv.appendChild(item);
        });
    }

    document.getElementById("save").addEventListener('click', function() {
        fetch('/save')
        .then(response => response.json())
        .then(data => alert(data))
        .catch(error => console.log('Error saving weather history:', error));
    });
};