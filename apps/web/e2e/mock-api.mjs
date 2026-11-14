// Tiny stand-in for the BudByte API so the web smoke test runs without Python.
import http from "node:http";

const port = Number(process.env.MOCK_API_PORT ?? 8765);
const routes = {
  "/healthz": [200, { status: "ok", version: "0.1.0-mock" }],
  "/readyz": [200, { status: "ok", checks: { database: "ok", redis: "ok" } }],
};

http
  .createServer((req, res) => {
    const hit = routes[req.url ?? ""];
    const [code, body] = hit ?? [404, { detail: "Not Found" }];
    res.writeHead(code, { "content-type": "application/json" });
    res.end(JSON.stringify(body));
  })
  .listen(port, () => console.log(`mock api on ${port}`));
