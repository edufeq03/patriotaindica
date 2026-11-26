FROM node:22-alpine AS builder

WORKDIR /app

ENV CI=true
ENV NEXT_TELEMETRY_DISABLED=1

ARG JWT_SECRET_KEY
ENV JWT_SECRET_KEY=$JWT_SECRET_KEY

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

COPY --chown=node:node --from=builder /app/public ./public
COPY --chown=node:node --from=builder /app/.next ./.next
COPY --chown=node:node --from=builder /app/node_modules ./node_modules
COPY --chown=node:node --from=builder /app/package.json ./package.json

USER node

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/api/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))" || exit 1

CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
