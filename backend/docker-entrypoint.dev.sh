#!/bin/sh
set -e

# compose waits on the db healthcheck, but the schema still has to exist
# before uvicorn starts serving requests against it.
alembic upgrade head

exec "$@"
