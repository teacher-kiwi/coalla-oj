FROM node:16-alpine AS builder
WORKDIR /app
RUN apk add --no-cache git
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build:dll && npm run build

FROM nginx:stable-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
WORKDIR /usr/share/nginx/html
COPY --from=builder /app/dist/ ./

EXPOSE 80

# ARG STATIC_CDN_HOST=""
# RUN if [ -n "$STATIC_CDN_HOST" ]; then \
#       find /usr/share/nginx/html -name "*.*" -type f -exec sed -i "s#__STATIC_CDN_HOST__#/$STATIC_CDN_HOST#g" {} \; ; \
#     else \
#       find /usr/share/nginx/html -name "*.*" -type f -exec sed -i "s#__STATIC_CDN_HOST__/##g" {} \; ; \
#     fi

# RUN find /usr/share/nginx/html -name "*.*" -type f -exec sed -i "s|__STATIC_CDN_HOST__||g" {} \;