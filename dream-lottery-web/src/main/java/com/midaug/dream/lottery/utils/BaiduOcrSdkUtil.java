package com.midaug.dream.lottery.utils;

import com.baidu.aip.ocr.AipOcr;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.HashMap;

/**
 * @className: BaiduOcrSdkUtil
 * @Description: TODO
 * @author: midaug
 * @date: 2021/11/10 10:43
 */
public class BaiduOcrSdkUtil {

    private static final Logger LOGGER = LoggerFactory.getLogger(BaiduOcrSdkUtil.class);

    public static String resultToString(JSONObject json) {
        if (json == null) {
            LOGGER.info("baiOcr result => " + json);
            return null;
        }
        if (json.has("error_code") && json.has("error_msg")) {
            LOGGER.info("baiOcr result => " + json);
            return null;
        }
        JSONArray array = json.getJSONArray("words_result");
        if (array == null || array.length() < 1) {
            return null;
        }
        StringBuffer sb = new StringBuffer();
        for (int i = 0; i < array.length(); i++) {
            sb.append(array.getJSONObject(i).get("words"));
        }
        LOGGER.info("baiOcr result => " + sb);
        return sb.toString();
    }

    public static void main(String[] args) {
    }

    public static JSONObject ocrImgPath(AipOcr client, String path) {
        return client.basicGeneral(path, new HashMap<>());
    }

    public static JSONObject ocrImgByBytes(AipOcr client, byte[] bytes) {
        return client.basicGeneral(bytes, new HashMap<>());
    }

    public static JSONObject ocrImgByBytes(AipOcr client, MultipartFile multipartFile) {
        byte[] bytes = {};
        if (multipartFile != null) {
            try {
                bytes = multipartFile.getBytes();
            } catch (IOException e) {
            }
        }
        bytes = bytes != null && bytes.length / 1000 > 1000 ? PicUtils.compressPicForScale(bytes, 1000) : bytes;
        return ocrImgByBytes(client, bytes);
    }

    public static String ocrImgToStringByBytes(AipOcr client, MultipartFile multipartFile) {
        return resultToString(ocrImgByBytes(client, multipartFile));
    }
}
