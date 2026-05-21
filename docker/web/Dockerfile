FROM node:24-alpine

# Install ttyd, tmux, bash, and redis-cli for workshop inspection
RUN apk add --no-cache ttyd tmux bash redis

WORKDIR /app

# Copy scripts and config
COPY start.sh /start.sh
COPY tmux.conf /etc/tmux.conf
RUN chmod +x /start.sh

# Expose both Vite and ttyd ports
EXPOSE 3000 7681

# Start tmux session and ttyd
CMD ["/start.sh"]
