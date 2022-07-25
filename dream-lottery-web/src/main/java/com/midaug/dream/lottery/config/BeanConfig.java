package com.midaug.dream.lottery.config;

import com.baidu.aip.ocr.AipOcr;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.stereotype.Component;

/**
 * @className: BeanConfig
 * @Description: TODO
 * @author: midaug
 * @date: 2021/11/10 10:51
 */
@Component
public class BeanConfig {

    private static final Logger LOGGER = LoggerFactory.getLogger(BeanConfig.class);

    @Value("${baidu.ocr.app.id:}")
    private String baidu_app_id;
    @Value("${baidu.ocr.app.key:}")
    private String baidu_app_key;
    @Value("${baidu.ocr.app.secret:}")
    private String baidu_app_secret;

    @Bean
    private AipOcr createAipOcr() {
        LOGGER.info("createBean AipOcr, appid={} appkey={} appsecret={}",
                StringUtils.defaultIfBlank(baidu_app_id, "x").substring(0, 1) + "-xxxxx",
                StringUtils.defaultIfBlank(baidu_app_key, "x").substring(0, 1) + "-xxxxx",
                StringUtils.defaultIfBlank(baidu_app_secret, "x").substring(0, 1) + "-xxxxx"
        );
        AipOcr client = new AipOcr(baidu_app_id, baidu_app_key, baidu_app_secret);
        client.setConnectionTimeoutInMillis(2000);
        client.setSocketTimeoutInMillis(60000);
//        // 可选：设置代理服务器地址, http和socket二选一，或者均不设置
//        client.setHttpProxy("proxy_host", proxy_port);  // 设置http代理
//        client.setSocketProxy("proxy_host", proxy_port);  // 设置socket代理
        return client;
    }
}
