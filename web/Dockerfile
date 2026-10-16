# Local run only: the Vite dev server, proxying /api to the api service.
FROM node:22.22.0-bookworm-slim
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY web/package.json web/
RUN HUSKY=0 pnpm install --frozen-lockfile --filter web...
COPY web web
WORKDIR /app/web
EXPOSE 5173
CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0"]
