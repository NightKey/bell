function updateButtons(optionName) {
    let selectedOption;
    all.forEach(option => {
        if (option.name === optionName) {
            selectedOption = option;
        }
    });
    let buttons = document.getElementsByTagName("button");
    for (let index = 0; index < buttons.length; index++) {
        const button = buttons[index];
        if (button.getAttribute("id") === "toggle" || button.getAttribute("id") == "average") continue;
        if (selectedOption !== undefined && button.getAttribute("id") !== selectedOption.state) {
            button.removeAttribute("disabled");
        } else {
            button.setAttribute("disabled", "true");
        }
    }
}

let selector = document.getElementById("options");

class Option {
    constructor(name, unit, color) {
        this.name = name;
        this.unit = unit;
        this.state = "off";
        this.color = color;
    }

    option() {
        let ret = document.createElement("option")
        ret.value = this.name;
        ret.innerText = this.name;
        return ret;
    }
}

let all = [];
let weatherHistoryData = [];
let chartConfig = {scrollZoom: true, modeBarButtonsToRemove: ["lasso2d", "zoomIn2d", "zoomOut2d", "resetScale2d", "select2d", "toggleSpikelines"]}
let useAverage = false;

function fillAll() {
    all.push(new Option("Temperature", weatherHistoryData[0].temperature_unit, "rgb(0, 255, 0)"));
    all.push(new Option("Heatindex", weatherHistoryData[0].temperature_unit, "rgb(214, 112, 0)"));
    all.push(new Option("Pressure", "mbar", "rgb(0, 0, 255)"));
    all.push(new Option("Humidity", "%", "rgb(139, 0, 206)"));
    all.push(new Option("Pressure_delta", "\u{394}mbar", "rgb(206, 0, 95)"));
}

function fillData() {
    all.forEach(item => {
        selector.appendChild(item.option());
    });
}

function mapWeatherHistoryData(name) {
    let accumulator = [];
    let startTime = "";
    let result = [];
    let firstRun = true;
    if (!useAverage) {
        return weatherHistoryData.map(item => Object.fromEntries(new Map([["time", item.time], ["data", item[name]]])));
    }
    weatherHistoryData.sort((item) => new Date(item.time)).forEach((item) => {
        currentTime = new Date(item.time)
        if (startTime == "" || currentTime - startTime > 3600000) {
            if (!firstRun) {
                result.push(Object.fromEntries(new Map([["time", startTime], ["data", accumulator.reduce((a, b) => a + b) / accumulator.length]])));
            } else {
                firstRun = false;
            }
            accumulator = [];
            startTime = currentTime;
        }
        accumulator.push(item[name]);
    });
    result.push(Object.fromEntries(new Map([["time", startTime], ["data", accumulator.reduce((a, b) => a + b) / accumulator.length]])));
    return result;
}

function updateCustomChart() {
    let chart_data = [];
    let y1Names = [];
    let y2Names = [];
    all.forEach(option => {
        if (option.state != "off") {
            let name = `${option.name} (${option.unit})`;
            let data = mapWeatherHistoryData(option.name.toLowerCase());
            mapWeatherHistoryData(option.name.toLowerCase());
            chart_data.push(
                {x: data.map(item => item.time), y: data.map(item => item.data), mode: "lines", name: name, yaxis: option.state.toLowerCase(), line: {color: option.color}}
            );
            if (option.state.toLowerCase() === "y1") {
                y1Names.push(name);
            } else {
                y2Names.push(name);
            }
        }
    });
    let chart_options = {
        title: "Custom chart",
        yaxis: {
            title: y1Names.join(' - ')
        },
        yaxis2: {
            title: y2Names.join(' - '),
            overlaying: 'y',
            side: 'right'
        },
        legend: {
            x: 0.5,
            y: -0.5
        }
    }
    Plotly.newPlot("chart", chart_data, chart_options, chartConfig);
}

function createCharts() {
    let temp_data = mapWeatherHistoryData("temperature");
    mapWeatherHistoryData("temperature"); //I have no idea, why it can't run correctly without calling this again.
    let humidity_data = mapWeatherHistoryData("humidity");
    mapWeatherHistoryData("humidity");
    let pressure_data = mapWeatherHistoryData("pressure");
    mapWeatherHistoryData("pressure");
    let temp_hum_chart_data = [
        {x: temp_data.map(item => item.time), y: temp_data.map(item => item.data), mode: "lines", name: `Temperature ${weatherHistoryData[0].temperature_unit}`, yaxis: "y"},
        {x: humidity_data.map(item => item.time), y: humidity_data.map(item => item.data), mode: "lines", name: "Humidity %", yaxis: "y2"}
    ];
    let temp_hum_oprtions = {
        title: "Temperature-Humidity",
        yaxis: {
            title: `Temperature ${weatherHistoryData[0].temperature_unit}`
        },
        yaxis2: {
            title: "Humidity %",
            overlaying: 'y',
            side: "right"
        },
        legend: {
            x: 0.5,
            y: -0.5
        }
    };
    let hum_press_chart_data =  [
        {x: humidity_data.map(item => item.time), y: humidity_data.map(item => item.data), mode: "lines", name: "Humidity %", yaxis: "y"},
        {x: pressure_data.map(item => item.time), y: pressure_data.map(item => item.data), mode: "lines", name: "Pressure mbar", yaxis: "y2"}
    ];
    let hum_press_oprtions = {
        title: "Humidity-Pressure",
        yaxis: {
            title: "Humidity %"
        },
        yaxis2: {
            title: "Pressure mbar",
            overlaying: 'y',
            side: "right"
        },
        legend: {
            x: 0.5,
            y: -0.5
        }
    };
    Plotly.newPlot("Temperature-Humidity", temp_hum_chart_data, temp_hum_oprtions, chartConfig);
    Plotly.newPlot("Humidity-Pressure", hum_press_chart_data, hum_press_oprtions, chartConfig);
}

function toggleClicked() {
    let containers = document.getElementsByClassName("container");
    for (let index = 0; index < containers.length; index++) {
        const item = containers[index];
        if (item.getAttribute("data-hide") === null) {
            if (item.classList.contains("hidden")) {
                item.classList.remove("hidden");
            } else {
                item.classList.add("hidden");
            }
        }
    }
    let button = document.getElementById("toggle");
    if (button.innerText === "Show custom chart") {
        button.innerText = "Show preset charts";
    } else {
        button.innerText = "Show custom chart";
    }
}

function toggleAverage() {
    let button = document.getElementById("average");
    button.innerText = button.innerText == "Show hourly average" ? "Show raw data" : "Show hourly average";
    useAverage = button.innerText == "Show raw data";
    updateCustomChart();
    createCharts();
}

window.onload = function() {
    fetch('/get?chart')
        .then(response => response.json())
        .then(data => {
            data.items.forEach(item => {
                weatherHistoryData.push(item);
            });
            createCharts();
            fillAll();
            fillData();
        })
        .catch(error => console.log('Error fetching historycal weather:', error));
    let buttons = document.getElementsByTagName("button");
    for (let index = 0; index < buttons.length; index++) {
        const button = buttons[index];
        if (button.getAttribute("id") === "toggle" || button.getAttribute("id") == "average") continue;
        button.addEventListener('click', function() {
            let selected = selector.selectedOptions[0].value;
            all.forEach(option => {
                if (option.name == selected) {
                    option.state = button.getAttribute('id');
                }
            });
            updateCustomChart();
            updateButtons(selected);
        });
    }
    selector.addEventListener("change", function() {
        let selected = selector.selectedOptions[0].value;
        updateButtons(selected);
    });
    document.getElementById("toggle").addEventListener("click", toggleClicked);
    document.getElementById("average").addEventListener("click", toggleAverage);
}
