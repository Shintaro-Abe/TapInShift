# syntax=docker/dockerfile:1

FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    bash \
    bubblewrap \
    ca-certificates \
    curl \
    fd-find \
    git \
    gnupg \
    iproute2 \
    jq \
    less \
    openssh-client \
    procps \
    python3 \
    python3-pip \
    ripgrep \
    unzip \
  && rm -rf /var/lib/apt/lists/*

RUN install -d -m 0755 /etc/apt/keyrings \
  && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
  && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends nodejs \
  && npm install -g @google/gemini-cli@latest \
  && rm -rf /var/lib/apt/lists/* \
  && node --version \
  && npm --version \
  && gemini --version

RUN install -d -m 0755 /etc/apt/keyrings \
  && curl -fsSL https://downloads.claude.ai/keys/claude-code.asc \
    -o /etc/apt/keyrings/claude-code.asc \
  && gpg --show-keys --with-colons /etc/apt/keyrings/claude-code.asc \
    | grep -q 'fpr:::::::::31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE:' \
  && echo "deb [signed-by=/etc/apt/keyrings/claude-code.asc] https://downloads.claude.ai/claude-code/apt/stable stable main" \
    > /etc/apt/sources.list.d/claude-code.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends claude-code \
  && rm -rf /var/lib/apt/lists/*

COPY .devcontainer/claude-no-print-wrapper.sh /tmp/claude-no-print-wrapper.sh

RUN install -d -m 0755 /usr/lib/claude-code \
  && mv /usr/bin/claude /usr/lib/claude-code/claude-real \
  && install -m 0755 /tmp/claude-no-print-wrapper.sh /usr/bin/claude \
  && rm /tmp/claude-no-print-wrapper.sh

ENV CODEX_HOME=/home/vscode/.codex
ENV CODEX_INSTALL_DIR=/usr/local/bin
ENV PATH="${CODEX_INSTALL_DIR}:${PATH}"

RUN mkdir -p "${CODEX_HOME}" /home/vscode/.claude /home/vscode/.gemini \
  && chown -R vscode:vscode "${CODEX_HOME}" /home/vscode/.claude /home/vscode/.gemini

RUN curl -fsSL https://chatgpt.com/codex/install.sh \
  | CODEX_NON_INTERACTIVE=1 CODEX_INSTALL_DIR="${CODEX_INSTALL_DIR}" sh \
  && codex --version \
  && claude --version

USER vscode
WORKDIR /workspaces
