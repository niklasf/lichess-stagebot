#!/bin/sh -e

echo "Compiling client ..."
./bin/prod/compile-client

export JAVA_OPTS="-Xms1024M -Xmx1024M -XX:ReservedCodeCacheSize=64m -XX:+UseConcMarkSweepGC"
sbt ";stage;exit"
