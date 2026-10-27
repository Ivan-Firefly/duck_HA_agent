FROM node:22-alpine
WORKDIR /app
COPY package.json duckai.js server.js install.js run.sh ./
# Integration shipped inside the image; install.js copies it into Home Assistant's config.
COPY custom_components /opt/integration/custom_components
RUN chmod +x /app/run.sh
EXPOSE 8787
CMD ["/app/run.sh"]
