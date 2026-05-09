FROM debian:trixie-slim AS builder
ARG TARGETARCH
ARG TARGETVARIANT

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,id=apt-cahce-1-$TARGETARCH$TARGETVARIANT-builder,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=apt-cahce-2-$TARGETARCH$TARGETVARIANT-builder,sharing=locked \
    <<EOS
set -ex
rm -f /etc/apt/apt.conf.d/docker-clean
echo 'APT::Install-Recommends "0";' > /etc/apt/apt.conf.d/no-recommends
echo 'APT::AutoRemove::RecommendsImportant "0";' >> /etc/apt/apt.conf.d/no-recommends
apt-get update
apt-get install -y --no-install-recommends libtool make cmake libseccomp-dev gcc python3 python3-venv
EOS

COPY Judger/ /app/
RUN <<EOS
set -ex
mkdir /app/build
cmake -S . -B build
cmake --build build --parallel $(nproc)
EOS

RUN <<EOS
set -ex
cd bindings/Python
python3 -m venv .venv
.venv/bin/pip3 install build
.venv/bin/python3 -m build -w
EOS

FROM debian:trixie-slim
ARG TARGETARCH
ARG TARGETVARIANT

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,id=apt-cahce-1-$TARGETARCH$TARGETVARIANT-final,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=apt-cahce-2-$TARGETARCH$TARGETVARIANT-final,sharing=locked \
    <<EOS
set -ex
rm -f /etc/apt/apt.conf.d/docker-clean
echo 'APT::Install-Recommends "0";' > /etc/apt/apt.conf.d/no-recommends
echo 'APT::AutoRemove::RecommendsImportant "0";' >> /etc/apt/apt.conf.d/no-recommends
needed="python3-minimal \
    python3-venv \
    libpython3-stdlib \
    libpython3-dev \
    golang-go \
    openjdk-21-jdk \
    gcc \
    g++ \
    nodejs \
    strace"
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg
mkdir -p /etc/apt/keyrings
curl -fsSL https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor -o /etc/apt/keyrings/adoptium.gpg
cat > /etc/apt/sources.list.d/adoptium.sources <<EOF
Types: deb
URIs: https://packages.adoptium.net/artifactory/deb
Suites: trixie
Components: main
Signed-By: /etc/apt/keyrings/adoptium.gpg
EOF
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
cat > /etc/apt/sources.list.d/nodesource.sources <<EOF
Types: deb
URIs: https://deb.nodesource.com/node_20.x
Suites: nodistro
Components: main
Signed-By:/etc/apt/keyrings/nodesource.gpg
EOF
apt-get update
apt-get install -y --no-install-recommends $needed
rm -rf /usr/lib/jvm/*/jmods
rm -rf /usr/lib/jvm/*/lib/src.zip
apt-get clean
rm -rf /var/lib/apt/lists/*
EOS

COPY --from=builder --chmod=755 --link /app/output/libjudger.so /usr/lib/judger/libjudger.so
COPY --from=builder /app/bindings/Python/dist/ /app/
RUN --mount=type=cache,target=/root/.cache/pip,id=pip-cahce-$TARGETARCH$TARGETVARIANT-final \
    <<EOS
set -ex
python3 -m venv .venv
CC=gcc .venv/bin/pip3 install --compile --no-cache-dir flask gunicorn idna psutil requests
.venv/bin/pip3 install *.whl
EOS

COPY server/ /app/
RUN <<EOS
set -ex
chmod -R u=rwX,go=rX /app/
chmod +x /app/entrypoint.sh
gcc -shared -fPIC -o unbuffer.so unbuffer.c
useradd -u 901 -r -s /sbin/nologin -M compiler
useradd -u 902 -r -s /sbin/nologin -M code
useradd -u 903 -r -s /sbin/nologin -M -G code spj
mkdir -p /usr/lib/judger
EOS

RUN <<EOS
set -ex
gcc --version
g++ --version
python3 --version
java -version
node --version
go version
EOS

HEALTHCHECK --interval=5s CMD [ "/app/.venv/bin/python3", "/app/service.py" ]
EXPOSE 8080
ENTRYPOINT [ "/app/entrypoint.sh" ]
