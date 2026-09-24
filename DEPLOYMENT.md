# Self-Hosted Deployment (Hostinger + Docker Hub)

## 1. Push code to GitHub
Use the **"Save to Github"** button in the Emergent chat input to push this repo to
`mishraramesh-design/mydesignermaster` (requires a paid Emergent plan).

## 2. GitHub Actions -> Docker Hub
`.github/workflows/docker-publish.yml` builds the single combined image (frontend + backend + nginx)
on every push to `main` and publishes it to Docker Hub as `mishramesh/mydesignermaster:latest`.
It uses the `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repo secrets you already configured — no changes needed there.

## 3. Deploy on Hostinger
Copy `docker-compose.yml` to your Hostinger server, then:

```bash
docker compose pull
docker compose up -d
```

The app will be available at `http://<your-server-ip>:4345`.

## IMPORTANT: LLM key
This app was built on Emergent using the **Emergent Universal LLM Key**, which only works
inside the Emergent platform. It will NOT work on your self-hosted server.

Before deploying, edit `docker-compose.yml` and replace:
```
EMERGENT_LLM_KEY: "REPLACE_WITH_YOUR_OWN_OPENAI_API_KEY"
```
with your own real OpenAI API key (starts with `sk-...`). The backend code works unchanged —
it only needs a valid key in that same env var name.

## Notes
- MongoDB runs as a container (`mongo`) with a persistent volume `mongo_data`. To use an external/managed
  Mongo instead, change the `MONGO_URL` env var and remove the `mongo` service.
- The frontend is built with `REACT_APP_BACKEND_URL=""` so it calls the API on the same origin (`/api/...`),
  which nginx reverse-proxies to the backend inside the same container. You don't need a separate backend URL.
- `.emergent/`, `/memory`, `/test_reports` are Emergent-internal build artifacts and are excluded from
  version control (see `.gitignore`); they are not required for self-hosted deployment.
