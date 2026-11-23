#!/bin/sh

if [ -n "$BACKEND_HOST" ]; then
  cat > /etc/nginx/conf.d/default.conf <<EOF
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;

  resolver 1.1.1.1 ipv6=off;

  location /api/ {
    proxy_pass https://$BACKEND_HOST;
    proxy_ssl_server_name on;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
  location = /sw.js { add_header Cache-Control "no-cache"; }
  location / { try_files \$uri /index.html; }
}
EOF
fi
