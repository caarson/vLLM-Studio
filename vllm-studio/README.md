# vLLM Studio

vLLM Studio is a professional management and monitoring suite for running multiple [vLLM](https://github.com/vllm-project/vllm) instances with a polished monochrome UI. It bundles a FastAPI manager that orchestrates per-model containers and provides an OpenAI-compatible proxy, plus a React dashboard that surfaces progress, resource estimates, and control flows.

![Dashboard Screenshot](docs/screenshot-placeholder.png)
![Chat Demo GIF](docs/chat-placeholder.gif)

## Prerequisites

- Docker Engine 24+
- Docker Compose v2
- NVIDIA GPU with drivers >= 525
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- Internet access for Hugging Face model downloads

Optional but recommended:

- `HUGGINGFACE_HUB_TOKEN` for improved rate limits and access to gated models.

## Quick start

```powershell
cd vllm-studio
# Ensure MANAGER_TOKEN is secret in your shell profile
$env:MANAGER_TOKEN = "super-secret-token"
docker compose up -d --build
```

Then open http://localhost:4000/.

1. Use **Add Model** to register a Hugging Face repo (e.g. `meta-llama/Llama-3.1-8B-Instruct`).
2. Press **Start** to launch a dedicated vLLM container. Watch download and load progress live.
3. Press **Use as Active** to route the OpenAI-compatible proxy.
4. Test the active model in the built-in chat drawer or via API requests to `POST http://localhost:4000/v1/chat/completions`.

Shutting down:

```powershell
docker compose down
```

## Environment variables

- `MANAGER_TOKEN` (required): bearer token enforced on all mutating operations.
- `HUGGINGFACE_HUB_TOKEN` (optional): forwarded to vLLM containers for private models.
- `CACHE_DIR` (optional): defaults to `/hf-cache`; override to change cache location.

## Project layout

```
vllm-studio/
├─ docker-compose.yml
├─ manager/
│  ├─ Dockerfile
│  ├─ app.py
│  ├─ requirements.txt
│  ├─ core/
│  │  ├─ catalog.py
│  │  ├─ docker_ctl.py
│  │  ├─ estimators.py
│  │  ├─ hf_utils.py
│  │  ├─ logs.py
│  │  ├─ models.py
│  │  ├─ progress.py
│  │  ├─ router.py
│  │  └─ settings_groups.py
│  ├─ static/
│  │  └─ index.html
│  └─ tests/
│     └─ test_api.py
└─ ui/
   ├─ Dockerfile
   ├─ package.json
   ├─ src/
   │  ├─ App.tsx
   │  ├─ main.tsx
   │  ├─ components/
   │  ├─ pages/
   │  └─ lib/
   ├─ tailwind.config.ts
   └─ vite.config.ts
```

## Tests

### Manager (Python)

```powershell
cd manager
pip install -r requirements.txt
pytest
```

### UI (React)

```powershell
cd ui
npm install
npm test
npm run build
Copy-Item -Recurse dist\* ..\manager\static\
```

## API Reference

### Catalog & lifecycle

- `GET /api/models`
- `POST /api/models`
- `DELETE /api/models/{name}`
- `POST /api/start`
- `POST /api/stop`
- `POST /api/route`

### Settings

- `GET /api/settings/{name}`
- `PUT /api/settings/{name}`
- `POST /api/restart`

### Progress & logs

- `GET /api/progress/{name}`
- `GET /api/logs/stream/{name}` (WebSocket)

### Proxy

- `POST /v1/chat/completions`

All mutating endpoints require `Authorization: Bearer $MANAGER_TOKEN`.

## Troubleshooting

- **`docker.errors.DockerException: Error while fetching server API version`** — Ensure Docker Desktop is running and the socket is mounted.
- **`failed to create shim` when starting models** — Confirm NVIDIA Container Toolkit is installed and `nvidia-smi` works on the host.
- **Slow downloads** — Provide `HUGGINGFACE_HUB_TOKEN` and verify network throughput on the host.
- **Permission denied for cache** — The `hf-cache` volume must be writable by UID 0 inside containers; reset with `docker volume rm vllm-studio-hf-cache` if needed.

## License

MIT
