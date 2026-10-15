FROM mcr.microsoft.com/devcontainers/base:jammy

# Use bash for RUN so pipefail is supported.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Keep in step with every other pixi pin (CI workflows, resources/docker/*.dockerfile,
# copilot-setup-steps.yml); tests/agent_harness/test_lockfile.py checks this.
ARG PIXI_VERSION=v0.63.2
ARG PIXI_SHA256_X86_64=b2a9e26bb6c80fe00618a02e7198dec222e1fbcec61e04c11b6e6538089ab100
ARG PIXI_SHA256_AARCH64=dbde6dbc2806602171e17305ce005e1aed519f2f2461a7cafd0093e92b7e7681

# Install pixi, verifying the download against the pinned SHA256 above.
RUN set -eu \
    && ARCH="$(uname -m)" \
    && case "${ARCH}" in \
        x86_64) PIXI_ARCH="x86_64"; PIXI_SHA256="${PIXI_SHA256_X86_64}" ;; \
        aarch64|arm64) PIXI_ARCH="aarch64"; PIXI_SHA256="${PIXI_SHA256_AARCH64}" ;; \
        *) echo "Unsupported architecture: ${ARCH}" >&2; exit 1 ;; \
       esac \
    && PIXI_ASSET="pixi-${PIXI_ARCH}-unknown-linux-musl.tar.gz" \
    && PIXI_BASE_URL="https://github.com/prefix-dev/pixi/releases/download/${PIXI_VERSION}" \
    && curl -fsSL --compressed -o /tmp/pixi.tar.gz "${PIXI_BASE_URL}/${PIXI_ASSET}" \
    && echo "${PIXI_SHA256}  /tmp/pixi.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/pixi.tar.gz -C /tmp pixi \
    && install -m 0755 /tmp/pixi /usr/local/bin/pixi \
    && rm -f /tmp/pixi /tmp/pixi.tar.gz \
    && pixi info

# set some user and workdir settings to work nicely with vscode
ENV VSCODE_HOME=/home/vscode \
    VSCODE_USER=vscode \
    SHELL=/bin/bash \
    PATH=/home/vscode/.local/bin:/home/vscode/.opencode/bin:${PATH}
USER ${VSCODE_USER}
WORKDIR ${VSCODE_HOME}

RUN echo 'eval "$(pixi completion -s bash)"' >> ${VSCODE_HOME}/.bashrc

# Pre-install the coding agent CLIs (Claude Code, Codex, Copilot CLI, OpenCode)
# so the devcontainer is ready on attach. The build context is the repository
# root (devcontainer.json sets "context": ".."), hence the .devcontainer/ prefix.
COPY --chown=vscode:vscode .devcontainer/install-agents.sh /tmp/install-agents.sh
RUN bash /tmp/install-agents.sh && rm -f /tmp/install-agents.sh
