FROM ghcr.io/prefix-dev/pixi:0.63.2 AS build

# copy source code, pixi.toml and pixi.lock to the container
COPY . /app
WORKDIR /app

# Remove any existing pixi environment (if any)
RUN rm -rf /app/.pixi

# Install git (required by hatch-vcs/setuptools-scm for version detection)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install the webservice pixi environment
RUN pixi install -e webservice
# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook -e webservice > /shell-hook.sh

# extend the shell-hook script to run the command passed to the container
RUN echo 'exec "$@"' >> /shell-hook.sh

FROM ubuntu:24.04 AS production

# only copy the production environment into prod container
# please note that the "prefix" (path) needs to stay the same as in the build container
COPY --from=build /app/.pixi/envs/webservice /app/.pixi/envs/webservice
COPY --from=build /shell-hook.sh /shell-hook.sh
# copy the source so editable installs resolve correctly
COPY --from=build /app/src /app/src
# copy admin seeding script
COPY --from=build /app/scripts/create_admin.py /app/scripts/create_admin.py

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser && mkdir -p /app/data/qc && chown -R appuser:appuser /app/data

WORKDIR /app
EXPOSE 8080

USER appuser

# set the entrypoint to the shell-hook script (activate the environment and run the command)
# no more pixi needed in the prod container
ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]
CMD ["uvicorn", "ca_biositing.webservice.main:app", "--host", "0.0.0.0", "--port", "8080"]
