package com.midaug.dream.lottery.utils;

import com.alibaba.fastjson.JSON;
import com.midaug.dream.lottery.dto.SSQDto;
import com.midaug.dream.lottery.dto.SSQImgOcrDto;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.math.NumberUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * @className: SSQUtil
 * @Description: TODO
 * @author: midaug
 * @date: 2021/11/9 10:37
 */
public class SSQUtil {

    private static final Logger LOGGER = LoggerFactory.getLogger(SSQUtil.class);

    private static final int MAXIMUM_NUMBER_OF_RETRIES = 3;

    /**
     * 将ssq img ocr识别结果文字转换为dto实体
     *
     * @param ocrResult:
     * @param ssqDto:
     * @return: com.midaug.dream.lottery.dto.SSQImgOcrDto
     * @Author midaug
     * @Date 2021-11-10 13:05:24
     */
    public static SSQImgOcrDto ocrResultToSSQImgOcrDto(String ocrResult, SSQDto ssqDto) {
        if (ssqDto == null || StringUtils.isBlank(ocrResult)) {
            return null;
        }
        SSQImgOcrDto dto = new SSQImgOcrDto();
        dto.setDrawDto(ssqDto);
        dto.setCode(ssqDto.getCode());
        dto.setDrawDate(ssqDto.getDrawDate());
        List<SSQImgOcrDto.NoteDto> noteDtos = new ArrayList<>();
        String str = StringUtils.replace(ocrResult, "-", "");
        str = StringUtils.replace(str, "：", "");
        str = StringUtils.replace(str, ".", "");
        str = StringUtils.replace(str, "/", "");
        str = StringUtils.replace(str, ">", "");
//        str = StringUtils.replace(str, " ", "");
//        str = str.replaceAll("[\\t\\n\\r]", "");
        str = StringUtils.chomp(str);
        str = StringUtils.strip(str);
        str = StringUtils.deleteWhitespace(str);
        dto.setOcr(str);
        str = StringUtils.toRootUpperCase(str);
        String[] harr = {"A", "B", "C", "D", "E", "F", "G", "8", "9"};
        for (String h : harr) {
            Pattern pattern = Pattern.compile(h + "\\d{14}");
            Matcher matcher = pattern.matcher(str);
            if (!matcher.find()) {
                continue;
            }
            String codeStr = matcher.group();
            if (codeStr.length() != 15) {
                continue;
            }
            str = StringUtils.remove(str, codeStr);
            String zm = codeStr.substring(0, 1);
            codeStr = codeStr.substring(1);
            List<String> fields = new ArrayList<>();
            fields.add(ssqDto.getCode());
            for (int i = 0; i < 7; i++) {
                String c = StringUtils.substring(codeStr, i * 2, i * 2 + 2);
                fields.add(c);
            }
            SSQImgOcrDto.NoteDto noteDto = new SSQImgOcrDto.NoteDto(fields.toArray(new String[]{}));
            noteDto.setZm(zm);
            noteDtos.add(noteDto);
            if (NumberUtils.isDigits(h) && noteDtos.size() >= 5) {
                break;
            }
        }
        dto.setNoteDtos(SSQUtil.whetherToWin(noteDtos, ssqDto));
        return dto;
    }

    /**
     * 补充奖品信息
     *
     * @param noteDtos:
     * @param ssqDto:
     * @return: java.util.List<com.midaug.dream.lottery.dto.SSQImgOcrDto.NoteDto>
     * @Author midaug
     * @Date 2021-11-10 13:05:11
     */
    public static List<SSQImgOcrDto.NoteDto> whetherToWin(List<SSQImgOcrDto.NoteDto> noteDtos, SSQDto ssqDto) {
        if (noteDtos == null || noteDtos.size() < 1 || ssqDto == null) {
            return noteDtos;
        }
        List<String> reds = Arrays.asList(ssqDto.getReds());
        noteDtos.forEach(dto -> {
            int redNum = 0;
            if (reds.contains(dto.getRed1())) {
                dto.setRed1f(true);
                redNum++;
            }
            if (reds.contains(dto.getRed2())) {
                dto.setRed2f(true);
                redNum++;
            }
            if (reds.contains(dto.getRed3())) {
                dto.setRed3f(true);
                redNum++;
            }
            if (reds.contains(dto.getRed4())) {
                dto.setRed4f(true);
                redNum++;
            }
            if (reds.contains(dto.getRed5())) {
                dto.setRed5f(true);
                redNum++;
            }
            if (reds.contains(dto.getRed6())) {
                dto.setRed6f(true);
                redNum++;
            }
            if (StringUtils.equals(ssqDto.getBlue1(), dto.getBlue1())) dto.setBlue1f(true);
            if (redNum == 6 && dto.isBlue1f()) {
                dto.setReward("一等奖");
                dto.setBonus(ssqDto.getBonus1());
            } else if (redNum == 6) {
                dto.setReward("二等奖");
                dto.setBonus(ssqDto.getBonus2());
            } else if (redNum == 5 && dto.isBlue1f()) {
                dto.setReward("三等奖");
                dto.setBonus("3000");
            } else if (redNum == 5 || (redNum == 4 && dto.isBlue1f())) {
                dto.setReward("四等奖");
                dto.setBonus("200");
            } else if (redNum == 4 || (redNum == 3 && dto.isBlue1f())) {
                dto.setReward("五等奖");
                dto.setBonus("10");
            } else if (dto.isBlue1f()) {
                dto.setReward("六等奖");
                dto.setBonus("5");
            }
        });
        return noteDtos;
    }


    /**
     * 从文字中解析期号
     *
     * @param result:
     * @return: java.lang.String
     * @Author midaug
     * @Date 2021-11-10 12:21:41
     */
    public static String subCodeByStr(String result) {
        String code = null;
        List<String[]> list = List.of(
                new String[]{"期号：", "序号"},
                new String[]{"期号：", "号"},
                new String[]{"期号:", "序号"},
                new String[]{"期号:", "号"},
                new String[]{"售期：", "-"},
                new String[]{"售期:", "-"},
                new String[]{"效期:", "销"},
                new String[]{"效期：", "销"}
        );
        for (String[] arr : list) {
            code = subCodeByStr(result, arr[0], arr[1], 7);
            if (StringUtils.isNotBlank(code)) {
                break;
            }
        }
        if (StringUtils.isBlank(code)) {
            for (String[] arr : list) {
                String[] rs = result.split(arr[0]);
                if (rs != null && rs.length >= 2 && StringUtils.length(rs[1]) >= 7) {
                    code = rs[1].substring(0,7);
                }
                if (StringUtils.isNotBlank(code)) {
                    break;
                }
            }
        }
        if (StringUtils.isBlank(code)) {
            return null;
        }
        return StringUtils.length(code) == 5 ? code : StringUtils.substring(code, 2, code.length());
    }

    private static String subCodeByStr(String result, String s, String e, int len) {
        String code = StringUtils.substringBetween(result, s, e);
        if (code == null || code.length() != len) {
            return null;
        }
        return code;
    }

    /**
     * 获取最新的ssq数据
     *
     * @param url:        请求链接
     * @param errorCount: 错误次数
     * @return: java.lang.String[]
     * @Author midaug
     * @Date 2021-11-09 12:06:06
     */
    public static String[] httpGetSSQData(String url, int errorCount) {
        try {
            var request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .GET()
                    .build();
            var client = HttpClient.newHttpClient();
            // 同步
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            int status = response == null ? -1 : response.statusCode();
            if (status == 200) {
                return response.body().split("[\r\n]+");
            } else {
                throw new RuntimeException("http error code is " + status);
            }
        } catch (Exception e) {
            // 最多重试3次
            if (errorCount >= MAXIMUM_NUMBER_OF_RETRIES) {
                LOGGER.error("http get ssq error(" + errorCount + "); " + e.getMessage(), e);
                return null;
            }
            try {
                Thread.sleep(1000);
            } catch (Exception e2) {
            }
            // 错误时重试
            return httpGetSSQData(url, errorCount + 1);
        }
    }

    public static String[] httpGetSSQData(String url) {
        return httpGetSSQData(url, 0);
    }

    public static void main(String[] args) {
        String str = "中国福利彩票\n" +
                "\n" +
                "CHINA WELFARE LOTTERY\n" +
                "\n" +
                "玩法：双色球-单式\n" +
                "\n" +
                "机号：31090671\n" +
                "\n" +
                "6E15-5806-F294-CAF6-C1B9/63707293/56CC1\n" +
                "\n" +
                "4.04\n" +
                "\n" +
                "07\n" +
                "\n" +
                "16\n" +
                "\n" +
                "29-16\n" +
                "\n" +
                "B.06\n" +
                "\n" +
                "15\n" +
                "\n" +
                "16\n" +
                "\n" +
                "26-12\n" +
                "\n" +
                "11\n" +
                "\n" +
                "05\n" +
                "\n" +
                "C.010\n" +
                "\n" +
                "31-05\n" +
                "\n" +
                "19\n" +
                "\n" +
                "D.061\n" +
                "\n" +
                "13\n" +
                "\n" +
                "32-07\n" +
                "\n" +
                "E.08 1226\n" +
                "\n" +
                "32-13\n" +
                "\n" +
                "开奖期：2022082 22-07-19\n" +
                "\n" +
                "合计10元\n" +
                "\n" +
                "销售期：2022082-115\n" +
                "\n" +
                "22-07-18 20:47:49\n" +
                "\n" +
                "周东路892号\n" +
                "\n" +
                "感谢您为公益慈普事业贡献3.60元\n" +
                "\n" +
                "上海市福利彩票发行中心承销";
        System.out.println(subCodeByStr(str));
        String ssq = "21045,06,09,01,21,25,22,07,8717208,324175,2021-04-27";
        ocrResultToSSQImgOcrDto(str, SSQDto.newSSQDto(ssq)).getNoteDtos().forEach((noteDto) -> {
            List<String> cs = new ArrayList<>();
            cs.add(noteDto.getZm());
            cs.addAll(Arrays.asList(noteDto.getReds()));
            cs.add(noteDto.getBlue1());
            System.out.println(JSON.toJSONString(cs));
        });
    }

}
