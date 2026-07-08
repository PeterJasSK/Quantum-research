#!/usr/bin/env bash

docker container run --rm -it \
    --user $(id --user):$(id --group) \
    --volume .:/thesis \
    kpituke/latex:2025.09.4 \
    make "$@"

