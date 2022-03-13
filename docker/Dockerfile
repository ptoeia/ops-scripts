#IMAGE:   Oracle-JDK-Image
#VERSION: Alpine-gblic:
#VERSION: JDK   :Oracle 1.8.0

FROM jeanblanchard/alpine-glibc
MAINTAINER goway
ENV UID 1500

ARG DIR_JAVA_HOME=/usr/local/share/java

ADD jdk8.tar.gz ${DIR_JAVA_HOME}

ENV JAVA_HOME ${DIR_JAVA_HOME}
ENV PATH      $PATH:${DIR_JAVA_HOME}/bin
ENV LANG      en_US.UTF8

#安装bash
RUN apk update \
    && apk upgrade \
    && apk add --no-cache bash bash-doc bash-completion \
    && rm -rf /var/cache/apk/*

RUN addgroup -g ${UID} admin \
    && adduser -h /home/admin -G admin -D -u ${UID} admin -s /bin/bash
