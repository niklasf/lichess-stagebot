FROM debian:testing

MAINTAINER Niklas Fiekas <niklas.fiekas@backscattering.de>

RUN apt-get update && apt-get install -y --no-install-recommends git-core nodejs openjdk-8-jdk-headless apt-transport-https gnupg
RUN apt-get install dirmngr

RUN echo "deb https://dl.bintray.com/sbt/debian /" > /etc/apt/sources.list.d/sbt.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2EE0EA64E40A89B84B2DF73499E82A75642AC823
RUN apt-get update && apt-get install -y sbt

RUN apt-get install -y npm nodejs-legacy
RUN npm install -g gulp-cli && npm install -g npm

RUN useradd --create-home --user-group builder

USER builder:builder
VOLUME /home/builder/lila
WORKDIR /home/builder/lila


COPY stage-deploy.sh /home/builder
COPY build-deps.sh /home/builder

RUN /home/builder/build-deps.sh

CMD ../stage-deploy.sh
