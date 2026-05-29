# syntax=docker/dockerfile:1

# ---- Stage 1: build -------------------------------------------------------
# Compile the TypeScript sources to dist/ with full dev dependencies present.
FROM node:20-slim AS build
WORKDIR /app

# Install dependencies first for better layer caching.
COPY package*.json ./
RUN npm ci || npm install

# Bring in everything tsc needs (tsconfig includes src, scripts, test).
COPY tsconfig.json ./
COPY src ./src
COPY scripts ./scripts
COPY test ./test

RUN npm run build

# ---- Stage 2: runtime -----------------------------------------------------
# Minimal runtime image: just package manifests, compiled output, and prod
# deps (there are none at runtime, so this stays tiny).
FROM node:20-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV JAROS_DATA_DIR=/data

COPY package*.json ./
RUN (npm ci --omit=dev || npm install --omit=dev) && npm cache clean --force

COPY --from=build /app/dist ./dist

# Create and own the data directory, then drop to a non-root user.
RUN mkdir -p /data \
    && chown -R node:node /data /app
USER node

CMD ["node", "dist/src/main.js"]
