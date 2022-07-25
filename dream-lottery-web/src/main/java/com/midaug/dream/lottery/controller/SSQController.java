package com.midaug.dream.lottery.controller;

import com.alibaba.fastjson.JSON;
import com.midaug.dream.lottery.dto.SSQDto;
import com.midaug.dream.lottery.dto.WebResult;
import com.midaug.dream.lottery.service.SSQService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.util.List;
import java.util.concurrent.Callable;

/**
 * @Author midaug
 * @Date 2021-11-09 13:41:04
 */
@Controller
@RequestMapping("/ssq")
public class SSQController {

    private static final Logger LOGGER = LoggerFactory.getLogger(SSQController.class);

    @Resource
    SSQService ssqService;

    @Value("${spring.mvc.async.request-timeout:30000}")
    private int request_timeout;

    /**
     * @return: java.lang.Object
     * @Author midaug
     * @Date 2021-11-08 18:22:52
     */
    @RequestMapping(value = "/index", name = "显示首页")
    public String index(Model model) {
        List<SSQDto> listData = ssqService.getSSQs();
        model.addAttribute("ssqList", listData);
        model.addAttribute("request_timeout", request_timeout);
        return "index";
    }

    /**
     * @return: java.lang.Object
     * @Author midaug
     * @Date 2021-11-08 18:22:52
     */
    @RequestMapping(value = "/sync", name = "更新数据")
    @ResponseBody
    public Callable<WebResult> syncData() {
        return () -> {
            ssqService.sycnSSQData();
            return WebResult.getWebResult(0, "ok");
        };
    }

    /**
     * @return: java.lang.Object
     * @Author midaug
     * @Date 2021-11-08 18:22:52
     */
    @RequestMapping(value = "/upload/img", name = "上传图片识别", produces = "application/json; charset=UTF-8")
    @ResponseBody
    public Callable<WebResult> uploadImg(@RequestParam("imgs") MultipartFile[] multipartFile) {
        return () -> {
            WebResult result = WebResult.getWebResult(-1, "Param imgs is none");
            if (multipartFile != null && multipartFile.length > 0) {
                result = ssqService.imgOcr(multipartFile[0]);
            }
            LOGGER.info("/upload/img R=> " + JSON.toJSONString(result));
            return result;
        };
    }

}
