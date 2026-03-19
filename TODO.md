# FaceTrack TODO

---

## 1. Reorganize root directory

Move all backend-related files out of the root into a `backend/` directory.
The root should only contain subdirectories, LICENSE, README.md, and .gitignore.

### Files to move

| File | Destination |
|---|---|
| `Dockerfile` | `backend/Dockerfile` |
| `docker-compose.linux.yml` | `backend/docker-compose.linux.yml` |
| `docker-compose.prod.yml` | `backend/docker-compose.prod.yml` |
| `.env` | `backend/.env` |
| `.dockerignore` | `backend/.dockerignore` |
| `run.sh` | `backend/run.sh` |
| `run-prod.sh` | `backend/run-prod.sh` |
| `app/` | `backend/app/` (Django project stays inside backend) |
| `scripts/` | `backend/scripts/` |

### Target root layout

```
ReconRoll/
├── backend/
│   ├── app/               # Django project
│   ├── scripts/
│   ├── Dockerfile
│   ├── docker-compose.linux.yml
│   ├── docker-compose.prod.yml
│   ├── .env
│   ├── .env.example
│   ├── .dockerignore
│   ├── run.sh
│   └── run-prod.sh
├── facetrack-frontend/    # Vite/React app
├── docs/
├── .gitignore
├── .gitmodules
├── LICENSE
└── README.md
```

### Steps
- [ ] Create `backend/` directory
- [ ] Move files listed above
- [ ] Update `Dockerfile` COPY paths if they reference relative paths (e.g. `./app/requirements.txt`)
- [ ] Update `docker-compose` volume mounts and build context paths
- [ ] Update `run.sh` / `run-prod.sh` paths
- [ ] Update `scripts/` paths that reference the app directory
- [ ] Update `.gitignore` if it has root-relative paths
- [ ] Test `docker compose -f backend/docker-compose.linux.yml up` still works

---

## 2. Production docker-compose for backend

A production compose file that copies the Django code into the image (no bind mounts).

### Steps
- [ ] Create `backend/docker-compose.prod.yml` (or update existing one)
- [ ] Set `build: context: .` pointing at `backend/`
- [ ] Remove dev bind mounts (`- ./app:/app`) — code should be baked into the image
- [ ] Add `DJANGO_MODE=production` env var
- [ ] Set `DEBUG=False` in prod env
- [ ] Add `collectstatic` step in Dockerfile (run before CMD)
- [ ] Use a named volume for media files only (`/vol/media`)
- [ ] Add `restart: unless-stopped` to all services
- [ ] Add a `db` service (postgres) with a named volume for persistence
- [ ] Add a `redis` service if task queuing is needed later
- [ ] Confirm uWSGI config is production-ready (no `--py-autoreload`)
- [ ] Create `backend/.env.prod.example` with all required keys documented

---

## 3. Nginx + self-signed TLS (dev/LAN)

Needed so `navigator.mediaDevices` works on external IPs (browsers require HTTPS for camera access).

### Steps
- [ ] Add an `nginx` service to `docker-compose.linux.yml`
- [ ] Create `backend/nginx/nginx.conf` — reverse proxy to uWSGI/Django on port 8000
- [ ] Generate a self-signed cert:
  ```bash
  mkdir -p backend/nginx/certs
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout backend/nginx/certs/selfsigned.key \
    -out backend/nginx/certs/selfsigned.crt \
    -subj "/CN=192.168.100.90"
  ```
- [ ] Mount certs into the nginx container:
  ```yaml
  volumes:
    - ./nginx/certs:/etc/nginx/certs:ro
    - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
  ```
- [ ] Expose port 443 on the nginx container, remove direct port 8000 exposure
- [ ] Update `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` in `.env` to use `https://`
- [ ] Update `facetrack-frontend/.env` `VITE_API_URL` to `https://192.168.100.90/api`
- [ ] Accept the self-signed cert warning in the browser once, then camera access will work
- [ ] For production: replace self-signed cert with Let's Encrypt (certbot) when a domain is available

### Minimal nginx.conf template

```nginx
server {
    listen 443 ssl;
    server_name 192.168.100.90;

    ssl_certificate     /etc/nginx/certs/selfsigned.crt;
    ssl_certificate_key /etc/nginx/certs/selfsigned.key;

    client_max_body_size 20M;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /vol/static/;
    }

    location /media/ {
        alias /vol/media/;
    }
}

server {
    listen 80;
    server_name 192.168.100.90;
    return 301 https://$host$request_uri;
}
```

---

## 4. Dockerize frontend (later)

- [ ] Create `facetrack-frontend/Dockerfile`
  - Build stage: `node:20-alpine`, run `npm run build`
  - Serve stage: `nginx:alpine`, copy `/dist` to nginx html root
- [ ] Add `frontend` service to `docker-compose.prod.yml`
- [ ] Nginx for frontend serves on port 80/443, proxies `/api/` to backend service
- [ ] Pass `VITE_API_URL` as a build arg so it gets baked into the bundle
- [ ] Consider a single nginx container that serves both frontend static files and proxies the backend

---

## Notes

- `cookies.txt` in root — check if this is needed or should be gitignored
- `docs/` can stay in root, it's fine there
- `.gitmodules` suggests a submodule — verify it still points to the right path after the `backend/` move
