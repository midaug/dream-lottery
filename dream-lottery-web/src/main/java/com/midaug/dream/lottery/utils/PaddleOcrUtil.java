package com.midaug.dream.lottery.utils;

import org.apache.commons.io.FileUtils;
import org.apache.commons.io.IOUtils;
import org.apache.commons.lang3.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.net.URL;

/**
 * @Date 2022-07-20 21:15:22
 */
public class PaddleOcrUtil {

    private static final Logger LOGGER = LoggerFactory.getLogger(PaddleOcrUtil.class);

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


    public static String ocrImgByBytes(String url, MultipartFile file) {
        byte[] bytes = {};
        if (file != null) {
            try {
                bytes = file.getBytes();
            } catch (IOException e) {
            }
        }
        bytes = bytes != null && bytes.length / 1000 > 1000 ? PicUtils.compressPicForScale(bytes, 1000) : bytes;
        RestTemplate client = new RestTemplate();
        MultiValueMap<String, Object> params = new LinkedMultiValueMap<>();
        ByteArrayResource fileAsResource = new ByteArrayResource(bytes) {
            @Override
            public String getFilename() {
                String name = file.getOriginalFilename();
                return StringUtils.isBlank(name) ? file.getName() : name;
            }

            @Override
            public long contentLength() {
                return file.getSize();
            }
        };
//        FileSystemResource fileSystemResource = new FileSystemResource("/Users/midaug/Downloads/WechatIMG259.jpeg");
        params.add("img", fileAsResource);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(params, headers);
        ResponseEntity rp = null;
        String rpBody = null;
        try {
            rp = client.exchange(url, HttpMethod.PUT, requestEntity, String.class);
            rpBody = rp.getBody().toString();
        } catch (HttpClientErrorException e) {
            rpBody = e.getResponseBodyAsString();
            LOGGER.warn("PaddleOcr result => " + e.getRawStatusCode() + " --- " + rpBody);

        }
        LOGGER.info("PaddleOcr result => " + rpBody);
        return rpBody;
    }

    public static void main(String[] args) throws IOException {
        byte[] bytes = FileUtils.readFileToByteArray(new File("/Users/midaug/Downloads/WechatIMG259.jpeg"));
        MultipartFile file = new MockMultipartFile("test.jpg", bytes);
        System.out.println(ocrImgByBytes("http://127.0.0.1:5000/ocr", file));
    }

}
