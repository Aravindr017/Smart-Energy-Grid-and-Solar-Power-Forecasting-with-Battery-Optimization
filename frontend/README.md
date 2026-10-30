# SOLARIS React dashboard

## Start the dashboard

From this directory, run:

```sh
npm install
npm run dev
```

The Vite development server starts the local FastAPI backend automatically when it is not already running and starts it again if it stops later. API requests wait for the backend to become ready before being proxied, avoiding transient 502 errors. It uses the project `.venv` or `venv` when available, otherwise `python` on Windows or `python3` on macOS/Linux. Open the URL printed by Vite (by default, `http://127.0.0.1:5173`). Stopping the Vite server also stops the backend it started.

Set `VITE_API_TARGET` to use an externally managed API instead; in that case Vite will not start a local backend.

The Overview defaults to plant-level 15-minute telemetry. Its capacity factor is computed for the selected plant as average measured AC power divided by rated capacity. Solar generation, capacity factor, and mean active power update when you switch plants or time resolution; these are historical measurements, not live telemetry.

## Other commands

- `npm run build` creates the production frontend bundle.
- `npm run lint` runs Oxlint.
