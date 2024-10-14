var server_port = 65432;
var server_addr = "192.168.86.32"; // the IP address of your Raspberry PI
var nodeConsole = require("console");
var myConsole = new nodeConsole.Console(process.stdout, process.stderr);
myConsole.log("Hello World!");
function client(name) {
    myConsole.log("client!");
    const net = require("net");

    const client = net.createConnection({ port: server_port, host: server_addr }, () => {
        // 'connect' listener.
        myConsole.log("connected to server!");
        // send the message
        client.write(`${name}\r\n`);
    });

    // get the data from the server
    client.on("data", (data) => {
        document.getElementById("greet_from_server").innerHTML = data;
        myConsole.log(data.toString());
        client.end();
        client.destroy();
    });

    client.on("end", () => {
        myConsole.log("disconnected from server");
    });
}

function greeting() {
    myConsole.log("greerings");
    // get the element from html
    var name = document.getElementById("myName").value;
    // update the content in html
    document.getElementById("greet").innerHTML = "Hello " + name + " !";
    // send the data to the server
    client(name);
}
