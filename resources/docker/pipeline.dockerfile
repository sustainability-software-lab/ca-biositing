FROM ghcr.io/prefix-dev/pixi:0.63.2 AS build

# copy source code, pixi.toml and pixi.lock to the container
COPY . /app
WORKDIR /app

# Remove any existing pixi environment (if any)
RUN rm -rf /app/.pixi

# Install git (required by hatch-vcs/setuptools-scm for version detection)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# run the `install` command (or any other). This will also install the dependencies into `/app/.pixi`
# assumes that you have a `prod` environment defined in your pixi.toml
RUN pixi install -e etl
# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook -e etl > /shell-hook.sh

# extend the shell-hook script to run the command passed to the container
RUN echo 'exec "$@"' >> /shell-hook.sh

FROM ubuntu:24.04 AS production

# only copy the production environment into prod container
# please note that the "prefix" (path) needs to stay the same as in the build container
COPY --from=build /app/.pixi/envs/etl /app/.pixi/envs/etl
COPY --from=build /shell-hook.sh /shell-hook.sh
# copy the source so editable installs resolve correctly
COPY --from=build /app/src /app/src

# Belt-and-suspenders: remove seed CSVs and geocode backups from the image.
# These files must never be baked in — the seed step reads from a volume-mounted
# path (SEED_CSV_PATH env var) or skips gracefully when the file is absent.
# Baking them in causes stale/incorrect data to be re-seeded on every run.
RUN find /app/src -name "seed_food_processor_facilities.csv" -delete \
 && find /app/src -name "geocode_backup_*.csv" -delete \
 || true
# copy alembic configuration and migrations
COPY --from=build /app/alembic.ini /app/alembic.ini
COPY --from=build /app/alembic /app/alembic
# copy Prefect flow entrypoint and deployment config
COPY --from=build /app/resources/prefect/run_prefect_flow.py /app/run_prefect_flow.py
COPY --from=build /app/resources/prefect/prefect.yaml /app/prefect.yaml

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser && chown -R appuser:appuser /app /shell-hook.sh

WORKDIR /app
EXPOSE 4200

USER appuser

# set the entrypoint to the shell-hook script (activate the environment and run the command)
# no more pixi needed in the prod container
ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]
