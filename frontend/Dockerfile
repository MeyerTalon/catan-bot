# Catan frontend for the local stack (docker-compose.yml `edge` service).
# Production serves the same `pnpm run build` output from S3 behind CloudFront;
# here nginx plays both roles (see nginx.conf). Build context is frontend/.
#   docker build --build-arg VITE_BACKEND_URL=http://localhost:8080/api frontend
FROM node:25-slim AS build
WORKDIR /app

# same pnpm as mise.toml / package.json packageManager
RUN npm install -g pnpm@11.20.0

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
# baked into the bundle at build time, like the deploy workflow does for prod
ARG VITE_BACKEND_URL
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}
RUN pnpm run build

FROM nginx:1.31-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
