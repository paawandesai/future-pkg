# Local run only: the Vite dev server, proxying /api to the api service.
FROM node:22.23.3-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY web/package.json web/
RUN HUSKY=0 pnpm install --frozen-lockfile --filter web...
COPY web web
WORKDIR /app/web
EXPOSE 5173
CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0"]
