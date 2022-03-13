#!/bin/bash
# 精简oracle jdk 包,重新打包jdk
#在当前目录解压jdk

set -ex 

TARGET_DIR='jdk'
IMAGE_ADDRESS='us-harbor.yuceyi.com/cf-images/base-java'
JDK_TAR_FILE=$1

if [ ! -n "${JDK_TAR_FILE}" ];then
    echo "请在参数中提供jdk tar包"
    exit 2 
fi

if [ ! -e  "./${JDK_TAR_FILE}" ];then
    echo "当前目录不存在jdk包${JDK_TAR_FILE}"
    exit 1 
fi

if [ ! -d  "./${TARGET_DIR}" ];then
    mkdir ./${TARGET_DIR}
else
    rm -rf ./${TARGET_DIR} 
    mkdir ./${TARGET_DIR}
fi

tar -zxvf ${JDK_TAR_FILE}  -C ./${TARGET_DIR} --strip-components 1 && cd ./${TARGET_DIR}

rm -rf COPYRIGHT LICENSE README release THIRDPARTYLICENSEREADME-JAVAFX.txt THIRDPARTYLICENSEREADME.txt Welcome.html
rm -rf     lib/plugin.jar \
           lib/ext/jfxrt.jar \
           bin/javaws \
           lib/javaws.jar \
           lib/desktop \
           plugin \
           lib/deploy* \
           lib/*javafx* \
           lib/*jfx* \
           lib/amd64/libdecora_sse.so \
           lib/amd64/libprism_*.so \
           lib/amd64/libfxplugins.so \
           lib/amd64/libglass.so \
           lib/amd64/libgstreamer-lite.so \
           lib/amd64/libjavafx*.so \
           lib/amd64/libjfx*.so

tar zcvf jdk8.tar.gz *
mv jdk8.tar.gz ../ && cd ../

read -p "输入镜像tag[e.g. v1]:" TAG 

docker build -t "${IMAGE_ADDRESS}:$TAG" .
