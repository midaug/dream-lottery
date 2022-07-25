package com.midaug.dream.lottery;

import com.alibaba.fastjson.JSON;
import com.baidu.aip.ocr.AipOcr;
import com.midaug.dream.lottery.utils.BaiduOcrSdkUtil;
import com.midaug.dream.lottery.utils.SSQUtil;
import org.json.JSONObject;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Arrays;
import java.util.HashMap;

//@SpringBootTest
class DreamLotteryWebApplicationTests {

    //    @Test
    void contextLoads() {
    }

    public static void testGetSSQ() {
        System.out.println("21124".length());
        String[] arr = SSQUtil.httpGetSSQData("https://gitee.com/midaug/dream-lottery/raw/main/spider_data/ssq.txts");
        for (String line : arr) {
            System.out.println(line);
        }
        System.out.println(arr.length);
    }

    public static void testOcrSDK() {
        String APP_ID = "";
        String API_KEY = "";
        String SECRET_KEY = "";
        // 初始化一个AipOcr
        AipOcr client = new AipOcr(APP_ID, API_KEY, SECRET_KEY);

        // 可选：设置网络连接参数
        client.setConnectionTimeoutInMillis(2000);
        client.setSocketTimeoutInMillis(60000);


        // 调用接口
        String path = "ssq.jpeg";
        JSONObject object = BaiduOcrSdkUtil.ocrImgPath(client, path);
        System.out.println(object);
    }

    public static void main(String[] args) throws Exception {
        testOcrSDK();
    }

}
