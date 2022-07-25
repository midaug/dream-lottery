FROM midaug/openjdk11:jdk-11.0.11_9

# 镜像作者信息
LABEL MAINTAINER midaug "blog.midaug.win"


ENV OPTS_JVM_OPTS="-Dserver.port=8080" \
 BAIDU_OCR_APPID="none" \
 BAIDU_OCR_APPKEY="none" \
 BAIDU_OCR_SECRET="none" \
 OPTS_NODE_MARK="none" \
 OPTS_OTHER=""

RUN mkdir -p /data/
COPY ./target/dream-lottery-web.jar /data/app.war

VOLUME ["/data/logs","/data/cache"]
WORKDIR  /data
EXPOSE 8080

CMD OPTS_NODE_MARK=`ifconfig eth0 | grep 'inet addr' | awk '{print $2}' | awk -F: '{print $2}'` && \
    cd /data && \
    java -Dbaidu.ocr.app.id=${BAIDU_OCR_APPID} \
        -Dbaidu.ocr.app.key=${BAIDU_OCR_APPKEY} \
        -Dbaidu.ocr.app.secret=${BAIDU_OCR_SECRET} \
        -Dhost.node=${OPTS_NODE_MARK} \
        -Djava.security.egd=file:/dev/./urandom \
        ${OPTS_JVM_OPTS} \
        ${OPTS_OTHER} \
        -jar /data/app.war