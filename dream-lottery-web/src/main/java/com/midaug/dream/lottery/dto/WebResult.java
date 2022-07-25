package com.midaug.dream.lottery.dto;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.serializer.SerializerFeature;
import org.apache.commons.lang3.StringUtils;

import java.util.HashMap;

/**
 * @className: WebResult
 * @Description: TODO
 * @author: midaug
 * @date: 2021/11/9 18:12
 */
public class WebResult extends HashMap<String, Object> {

    public static final WebResult SERVER_TIME_OUT = getWebResult(-1, "server time out");

    public WebResult() {
    }

    public static final WebResult newInstance(int code, String msg, Object data, Object attr) {
        return new WebResult().putV("code", code)
                .putV("msg", msg)
                .putV("data", data)
                .putV("attr", attr);
    }

    public WebResult putV(String key, Object v) {
        if (StringUtils.isBlank(key)) {
            return this;
        }
        super.put(key, v);
        return this;
    }

    public static final WebResult getSuccWebResult(int code, Object data) {
        return newInstance(code, "success", data, null);
    }

    public static final WebResult getSuccWebResult(int code, Object data, Object attr) {
        return newInstance(code, "success", data, attr);
    }

    public static final WebResult getWebResult(int code, String msg) {
        return newInstance(code, msg, null, null);
    }

    public static final WebResult getWebResult(int code) {
        return newInstance(code, null, null, null);
    }

    public String toJson(SerializerFeature... features) {
        return features == null ? JSON.toJSONString(this) : JSON.toJSONString(this, features);
    }

    public String toJson() {
        return JSON.toJSONString(this);
    }


}
