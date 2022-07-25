package com.midaug.dream.lottery.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.RequestMapping;

/**
 * @Author midaug
 * @Date 2021-11-09 13:41:04
 */
@Controller
public class IndexController {

    @RequestMapping(value = {"/", "/index", "/index.html", "/index.htm"}, name = "显示首页")
    public String index(Model model) {
        return "redirect:/ssq/index";

    }

}
