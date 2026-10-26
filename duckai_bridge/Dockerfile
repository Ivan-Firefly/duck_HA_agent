ARG BUILD_FROM=node:22-alpine
FROM ${BUILD_FROM}
WORKDIR /app
COPY package.json duckai.js server.js ./
ENV HOST=0.0.0.0 PORT=8787
EXPOSE 8787
USER node
CMD ["node", "server.js"]
