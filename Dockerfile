FROM debian:testing

RUN apt-get update && apt-get install -y --no-install-recommends git-core nodejs openjdk-8-jdk-headless apt-transport-https gnupg dirmngr npm nodejs-legacy

RUN echo "deb https://dl.bintray.com/sbt/debian /" > /etc/apt/sources.list.d/sbt.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2EE0EA64E40A89B84B2DF73499E82A75642AC823
RUN apt-get update && apt-get install -y sbt

RUN npm install -g npm && npm install -g npm
RUN npm install -g gulp-cli

RUN useradd --create-home --user-group builder

VOLUME /home/builder/lila
WORKDIR /home/builder/lila

COPY build-deps.sh /home/builder/build-deps.sh

RUN /home/builder/build-deps.sh
