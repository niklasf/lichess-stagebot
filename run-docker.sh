#!/bin/sh -e

docker build -t lila-buildenv .
docker run --volume /home/niklas/Projekte/lila:/home/builder/lila --user $(id -u) lila-buildenv
