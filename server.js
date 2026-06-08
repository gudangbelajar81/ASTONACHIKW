const http = require("http");
const path = require("path");
const next = require("./frontend/node_modules/next");

const port = Number(process.env.PORT || 3001);
const hostname = process.env.HOST || "0.0.0.0";
const dir = path.join(__dirname, "frontend");
const app = next({ dev: false, hostname, port, dir });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  http
    .createServer((req, res) => {
      handle(req, res);
    })
    .listen(port, hostname, () => {
      console.log(`AstroCycle frontend ready on http://${hostname}:${port}`);
    });
});
