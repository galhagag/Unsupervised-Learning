# Deploying on free-tier platforms

The app ships as a single Docker container: FastAPI serves both the API and
the built React frontend on `$PORT`. Everything below uses the `Dockerfile`
at the repo root.

## Before you pick a platform — two things to know

1. **State is ephemeral unless you mount a volume.** Your profile, deals,
   property ledger, history DB and manually-added listings live in SQLite/JSON
   under `DATA_DIR` (default `/data` in the container). Platforms without a
   persistent disk (Render free, HF Spaces free) reset that on every
   redeploy/restart. The curated/researched listings and all analysis are
   unaffected — they're baked into the image.
2. **Login is built in (HTTP Basic).** Set `AUTH_USERNAME` (default `gal`)
   and `AUTH_PASSWORD` as environment variables on the platform - the browser
   prompts for them on first visit. If `AUTH_PASSWORD` is unset the app runs
   open, so always set it on a public deployment. Never commit the password
   to the repo; `/api/health` stays open for platform health checks.

## Option A — Render (easiest, fully free)

1. Push this repo to GitHub (already done if you're reading this on the PR branch).
2. In [Render](https://dashboard.render.com): **New + → Blueprint** → connect
   the repo → it picks up `render.yaml` → **Apply**.
3. Optional: set `ANTHROPIC_API_KEY` in the service's Environment tab to
   enable LLM listing extraction (without it the regex fallback is used).
4. Your app is at `https://relocation-investment-explorer.onrender.com`.

Free-tier behavior: the service **spins down after ~15 min idle** — the first
request after a pause takes ~30-60 s to cold-start. 750 free instance-hours/mo
covers one always-available service. **No persistent disk on the free plan**:
profile/deals reset whenever the service redeploys or restarts. Good for
evaluating listings; record real deals somewhere durable too.

## Option B — Hugging Face Spaces (free + private access control)

1. Create a new **Space** at huggingface.co/new-space → SDK: **Docker** →
   visibility: **Private** (only you, logged in, can open it — free).
2. Push this repo to the Space (`git remote add hf https://huggingface.co/spaces/<you>/<space> && git push hf <branch>:main`).
3. In Space **Settings → Variables and secrets**, add `ANTHROPIC_API_KEY`
   (secret) if you want LLM extraction.

Spaces inject `PORT=7860` automatically — the image honors it. Free hardware
(2 vCPU / 16 GB) is plenty; the Space sleeps after ~48 h of inactivity and
wakes on visit. Filesystem is ephemeral on free (persistent storage is a paid
add-on at `/data` — if you later buy it, nothing to change: `DATA_DIR` already
points there).

## Option C — Google Cloud Run (most generous always-free, CLI required)

```bash
gcloud run deploy relocation-explorer --source . --region europe-west1 \
  --allow-unauthenticated --memory 512Mi --max-instances 1 \
  --set-env-vars EXTRACTOR_MODEL=claude-sonnet-4-6
# optional: --set-secrets ANTHROPIC_API_KEY=anthropic-key:latest
```

Always-free tier: 2M requests + 360k vCPU-seconds/mo — far more than this app
will use; scale-to-zero means it costs nothing idle. Filesystem is ephemeral
(in-memory); same state caveat as Render. Swap `--allow-unauthenticated` for
IAM auth if you want it private.

## Option D — Fly.io (cheapest path to PERSISTENT state, ~$2-3/mo, not free)

The one to pick when you start tracking a real deal and want the profile,
deal stages and ledger to survive restarts:

```bash
fly launch --copy-config --no-deploy     # uses fly.toml at the repo root
fly volumes create data --size 1 --region fra
fly secrets set AUTH_PASSWORD=<your-password> ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

`fly.toml` mounts the volume at `/data` (= `DATA_DIR`), and scale-to-zero
keeps the bill near the floor.

## Environment variables (all platforms)

| Var | Required | Purpose |
|---|---|---|
| `PORT` | injected by platform | Listen port (defaults to 8000) |
| `DATA_DIR` | no (default `/data`) | Writable state: SQLite DBs, manual/live listings |
| `AUTH_USERNAME` | no (default `gal`) | Basic-auth username |
| `AUTH_PASSWORD` | **yes on public deployments** | Basic-auth password; unset = app runs open |
| `ANTHROPIC_API_KEY` | no | Enables Claude extraction for pasted listings |
| `EXTRACTOR_MODEL` | no (default `claude-sonnet-4-6`) | Extraction model override |
| `SCRAPER_PROXY` | no | Proxy for portal scrapers if the host IP gets blocked |

## Verifying a deployment

```bash
curl https://<your-url>/api/cities          # ["Sofia","Sicily","Athens"]
curl https://<your-url>/api/recommendation | head -c 300
```

Then open the URL — the Best Pick tab should render with the top pick for the
default profile. Note: the portal scrapers now run from a cloud IP with open
internet — "Refresh live listings" becomes genuinely usable, though datacenter
IPs are more likely to be bot-challenged than residential ones (the status
line reports per-portal results; `SCRAPER_PROXY` is the workaround).

## Local smoke test of the production image

```bash
docker build -t rie .
docker run -p 8000:8000 -e PORT=8000 rie
# open http://localhost:8000
```
