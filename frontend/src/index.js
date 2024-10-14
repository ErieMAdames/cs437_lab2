document.onkeydown = updateKey;
document.onkeyup = resetKey;
const server_port = 65432;
const server_port_scan = 65433;
const server_addr = "192.168.86.32"; // the IP address of your Raspberry PI

const nodeConsole = require("console");
const myConsole = new nodeConsole.Console(process.stdout, process.stderr);
const map = Array.from({ length: 100 }, () => Array(100).fill(0));
// TODO scannnnn
function client(input) {
    const net = require("net");
    const client = net.createConnection({ port: server_port, host: server_addr }, () => {
        client.write(input);
    });
    client.on("data", (data) => {
        const receivedData = JSON.parse(data.toString());
        myConsole.log(receivedData);
        document.getElementById("temperature").innerHTML = " " + receivedData["cpuTemp"] + " C";
        document.getElementById("speed").innerHTML = " " + receivedData["speed"].toFixed(2) + " cm/S";
        document.getElementById("distance").innerHTML = " " + receivedData["distanceTraveled"].toFixed(2) + " cm";
        document.getElementById("direction").innerHTML = " " + (-(receivedData["angle"].toFixed(2) % 360)) + " degrees";
        document.getElementById("directionArrow").style.transform = `rotate(${-receivedData["angle"].toFixed(2) % 360}deg)`;
        document.getElementById("voltage").innerHTML = " " + receivedData["battery"].toFixed(2) + " V";
        if (receivedData["scanning"]) {
            if (receivedData["x"] >= 0 && receivedData["x"] < 100 && receivedData["y"] >= 0 && receivedData["y"] < 100) {
                map[receivedData["y"]][receivedData["x"]] = receivedData["obstacle"];
                drawGrid(receivedData["current_angle"], receivedData["x"], receivedData["y"]);
            } else {
                drawGrid(receivedData["current_angle"]);
            }
        }
        client.end();
        client.destroy();
    });

    client.on("end", () => {
        myConsole.log("disconnected from server");
    });
}

// for detecting which key is been pressed w,a,s,d
function updateKey(e) {
    e = e || window.event;

    myConsole.log(e.keyCode);
    if (e.keyCode === 87) {
        // up (w)
        document.getElementById("upArrow").classList.add("active");
        client("up");
    } else if (e.keyCode === 83) {
        // down (s)
        document.getElementById("downArrow").classList.add("active");
        client("down");
    } else if (e.keyCode === 65) {
        // left (a)
        document.getElementById("leftArrow").classList.add("active");
        client("left");
    } else if (e.keyCode === 68) {
        // right (d)
        document.getElementById("rightArrow").classList.add("active");
        client("right");
    } else if (e.keyCode === 75) {
        const currentForwardSpeed = document.getElementById("forwardSpeed").value;
        document.getElementById("forwardSpeed").value = Math.max(parseInt(currentForwardSpeed) - 1, 0);
        currentForwardSpeedSlider(Math.max(parseInt(currentForwardSpeed) - 1, 0));
    } else if (e.keyCode === 76) {
        const currentForwardSpeed = document.getElementById("forwardSpeed").value;
        document.getElementById("forwardSpeed").value = Math.min(parseInt(currentForwardSpeed) + 1, 100);
        currentForwardSpeedSlider(Math.min(parseInt(currentForwardSpeed) + 1, 100));
    }
}

// reset the key to the start state
function resetKey(e) {
    e = e || window.event;

    if ([87, 83, 65, 68].includes(e.keyCode)) {
        document.getElementById("upArrow").classList.remove("active");
        document.getElementById("downArrow").classList.remove("active");
        document.getElementById("leftArrow").classList.remove("active");
        document.getElementById("rightArrow").classList.remove("active");
        client("stop");
    }
}
function currentForwardSpeedSlider(speed) {
    const currentForwardSpeedEl = document.querySelector(".currentForwardSpeed");
    currentForwardSpeedEl.innerHTML = speed;
    client("speed:" + speed);
}
// update data for every 50ms
function scan() {
    for (let i = 0; i < map.length; i++) {
        for (let j = 0; j < map[i].length; j++) {
            map[i][j] = 0;
        }
    }
    client("scan");
}
setInterval(function () {
    client("update");
}, 50);
function drawGrid(angle = null, ax = null, ay = null) {
    const canvas = document.getElementById("gridCanvas");
    const ctx = canvas.getContext("2d");
    const cellSize = 5; // Size of each cell in the grid (in pixels)
    const buffer = 10; // Buffer around each black cell
    const numRows = map.length;
    const numCols = map[0].length;

    // Set the canvas background color to green
    ctx.fillStyle = "green";
    ctx.fillRect(0, 0, canvas.width, canvas.height); // Fill the entire canvas with green

    const canvasCenterX = canvas.width / 2; // X coordinate of the bottom middle
    const canvasBottomY = canvas.height; // Y coordinate of the bottom of the canvas

    // Draw circles for the grid points
    for (let row = 0; row < numRows; row++) {
        for (let col = 0; col < numCols; col++) {
            if (map[row][col] === 1) {
                ctx.fillStyle = "red";

                // Flip the y-coordinate to draw from bottom to top
                const flippedRow = numRows - 1 - row;

                // Calculate the center of the circle with buffer
                const x = col * cellSize + cellSize / 2;
                const y = flippedRow * cellSize + cellSize / 2;
                const radius = cellSize / 2 + buffer; // Increase radius to add buffer

                // Draw the circle
                ctx.beginPath();
                ctx.arc(x, y, radius, 0, Math.PI * 2); // Draw a full circle
                ctx.fill();
            }
        }
    }

    // If an angle is provided, draw a line across the entire canvas
    if (angle !== null) {
        console.log(angle);
        ctx.strokeStyle = "white"; // Red for angle-based lines
        ctx.beginPath();
        ctx.moveTo(canvasCenterX, canvasBottomY); // Start at the bottom middle of the canvas

        // Flip the y-coordinate to draw from bottom to top
        const flippedRow = numRows - 1 - ay;

        // Calculate the center of the circle with buffer
        const x = !!ax && !!ay ? ax * cellSize + cellSize / 2 : 0;
        const y = !!ax && !!ay ? flippedRow * cellSize + cellSize / 2 : 0;
        // Calculate the end points of the line using the angle
        const radians = (angle + 90) * (Math.PI / 180); // Convert the angle to radians
        const lineLength = 10000; // Extend line to cover canvas

        // Calculate the end coordinates based on the angle
        const endX = !!ax && !!ay ? x : canvasCenterX + lineLength * Math.cos(radians);
        const endY = !!ax && !!ay ? y : canvasBottomY - lineLength * Math.sin(radians); // Subtract because canvas Y grows downward

        ctx.lineTo(endX, endY); // Draw the line to the calculated end point
        ctx.stroke();
    }
}

document.addEventListener("DOMContentLoaded", drawGrid);
