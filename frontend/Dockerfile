FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./

# --- dev target: used by docker-compose.yml ---
FROM base AS dev

RUN npm ci

EXPOSE 3000

CMD ["npm", "run", "dev"]

# --- prod target: used by docker-compose.prod.yml ---
FROM base AS builder

RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

FROM node:20-alpine AS prod

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder --chown=app:app /app/public ./public
COPY --from=builder --chown=app:app /app/.next/standalone ./
COPY --from=builder --chown=app:app /app/.next/static ./.next/static

USER app

EXPOSE 3000

CMD ["node", "server.js"]
