#!/bin/bash

# Create or recreate the tmux session
create_session() {
  tmux -f /etc/tmux.conf new-session -d -s workshop -c /app
  tmux send-keys -t workshop 'npm install' Enter
  tmux send-keys -t workshop 'npm run dev' Enter
}

# Initial session creation
if ! tmux has-session -t workshop 2>/dev/null; then
  create_session
fi

# Start ttyd with a wrapper script that ensures session exists before attaching
# This allows multiple clients (no --once) while still recreating the session if it dies
ttyd -W -p 7681 bash -c '
  if ! tmux -f /etc/tmux.conf has-session -t workshop 2>/dev/null; then
    tmux -f /etc/tmux.conf new-session -d -s workshop -c /app
    tmux send-keys -t workshop "npm install" Enter
    tmux send-keys -t workshop "npm run dev" Enter
  fi
  exec tmux -f /etc/tmux.conf attach-session -t workshop
'

