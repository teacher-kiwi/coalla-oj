FROM node:20-alpine AS builder
WORKDIR /app
RUN apk add --no-cache git
COPY package*.json ./
RUN npm install
COPY . .

# 루트 .env 의 값을 compose 가 빌드 인자로 넘겨준다.
# vite 는 VITE_ 접두사가 붙은 환경변수를 번들에 포함시킨다.
ARG VITE_VERSION=""
ENV VITE_VERSION=$VITE_VERSION
RUN npm run build

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