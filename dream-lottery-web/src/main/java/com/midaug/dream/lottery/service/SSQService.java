package com.midaug.dream.lottery.service;

import com.baidu.aip.ocr.AipOcr;
import com.midaug.dream.lottery.dto.SSQDto;
import com.midaug.dream.lottery.dto.SSQImgOcrDto;
import com.midaug.dream.lottery.dto.WebResult;
import com.midaug.dream.lottery.utils.BaiduOcrSdkUtil;
import com.midaug.dream.lottery.utils.FileUtil;
import com.midaug.dream.lottery.utils.PaddleOcrUtil;
import com.midaug.dream.lottery.utils.SSQUtil;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.RandomUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.math.NumberUtils;
import org.apache.commons.lang3.time.DateFormatUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.io.File;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * @className: SSQService
 * @Description: TODO
 * @author: midaug
 * @date: 2021/11/9 10:35
 */
@Service
public class SSQService {


    private static final Logger LOGGER = LoggerFactory.getLogger(SSQService.class);

    /**
     * ssq cache
     */
    private final Map<String, SSQDto> ssqData = new ConcurrentHashMap<>();
    private final Map<String, Object> ssqCache = new ConcurrentHashMap<>();
    private static String NEW_SSQ_CODE = "NEW_SSQ_CODE"; //最新期号
    private static String NEW_SSQ_NUM = "NEW_SSQ_NUM"; //总开奖期数
    private static String NEW_SSQ_TIME = "NEW_SSQ_TIME"; //更新时间
    private static String SSQ_SORT_LIST = "SSQ_SORT_LIST"; //记录所有的红球
    private static String SSQ_REDS = "SSQ_REDS"; //记录所有的红球
    private static String SSQ_BLUES = "SSQ_BLUES"; //记录所有的篮球
    private static String SSQ_CODESS = "SSQ_CODESS"; //记录所有的组合，用来校验与历史是否重复
    private static String SSQ_RED_COUNTS = "SSQ_RED_COUNTS"; //历史开奖所有红球出现的次数
    private static String SSQ_BLUE_COUNTS = "SSQ_BLUE_COUNTS"; //历史开奖所有蓝球出现的次数

    @Value("${lottery.ssq.url}")
    private String lottery_ssq_url;

    @Value("${lottery.ssq.img.cache.dir}")
    private String cache_dir;

    @Value("${lottery.ssq.img.cache.days:7}")
    private int cache_days;

    @Value("${paddle.ocr.url}")
    String paddleOcrUrl;

    @Resource
    AipOcr client;

    /**
     * 获取最新一期的ssq开奖结果
     *
     * @return: com.midaug.dream.lottery.dto.SSQDto
     * @Author midaug
     * @Date 2021-11-09 13:42:56
     */
    public SSQDto getNewSSQ() {
        return (SSQDto) ssqCache.get(NEW_SSQ_CODE);
    }

    /**
     * 获取所有开奖结果
     *
     * @return: java.util.List<com.midaug.dream.lottery.dto.SSQDto>
     * @Author midaug
     * @Date 2021-11-09 13:44:04
     */
    public List<SSQDto> getSSQs() {
        if (ssqCache.get(SSQ_SORT_LIST) == null) {
            return Collections.EMPTY_LIST;
        }
        return ((List<SSQDto>) ssqCache.get(SSQ_SORT_LIST)).subList(0, 5);
    }

    /**
     * 图片识别是否中奖
     *
     * @param multipartFile:
     * @return: com.midaug.dream.lottery.dto.WebResult
     * @Author midaug
     * @Date 2021-11-10 12:14:22
     */
    public WebResult imgOcr(MultipartFile multipartFile) {
//        String ocrResult = BaiduOcrSdkUtil.ocrImgToStringByBytes(client, multipartFile);
        String ocrResult = StringUtils.isNotBlank(paddleOcrUrl) ? PaddleOcrUtil.ocrImgByBytes(paddleOcrUrl, multipartFile) :
                BaiduOcrSdkUtil.ocrImgToStringByBytes(client, multipartFile);
        // 中国福利彩票CHINA WELFARE LOTTERY588A3CB5DB4A7ESF9F11107C站号：310302262021，0426-12：03：51操作员：1
        // 双色球期号：2021045序号：00002单式
        // 红球蓝球A>06091724262707B>04051821303310C>01031221222909D>0104：0911263008E>03041415162501
        // 开奖日：2021-04-27倍数：001金额：10元站址：龙兰路277号地下二层B1-18号感谢您为社会福利事业贡献3，60元BDBE CE78B4A9734F上海市福利彩票发行中心承销
        long size = multipartFile == null ? -1 : multipartFile.getSize();
        String sizeStr = FileUtil.getNetFileSizeDescription(size);
        if (StringUtils.isNotBlank(cache_dir) && size > 0) {
            try {
                String fileName = DateFormatUtils.format(System.currentTimeMillis(), "yyyyMMdd_hhmmss_")
                        + UUID.randomUUID().toString().replaceAll("-", "");
                File file = new File(String.format("%s/%s.jpg", cache_dir, fileName));
                FileUtils.forceMkdirParent(file);
                FileUtils.writeByteArrayToFile(file, multipartFile.getBytes());
            } catch (Exception e) {
            }
        }
        if (StringUtils.isBlank(ocrResult)) {
            return WebResult.getWebResult(-1, "图片无法识别").putV("imageSize", sizeStr);
        }
        String code = SSQUtil.subCodeByStr(ocrResult);
        SSQDto ssqDto = code == null ? null : ssqData.get(code);
        if (ssqDto == null) {
            return WebResult.getWebResult(-1, "未找到开奖信息，期号：" + code).putV("imageSize", sizeStr);
        }
        SSQImgOcrDto dto = SSQUtil.ocrResultToSSQImgOcrDto(ocrResult, ssqDto);
        return WebResult.getSuccWebResult(200, dto).putV("imageSize", sizeStr);
    }

    /**
     * 按历史随机
     *
     * @param num:    随机num次
     * @param repeat: 是否接受与历史重复
     * @return: java.util.List<java.util.List < java.lang.String>>
     * @Author midaug
     * @Date 2021-11-09 14:24:14
     */
    public List<List<String>> randomHistorySSQs(int num, boolean repeat) {
        List<String> reds = (List<String>) ssqCache.get(SSQ_REDS);
        List<String> blues = (List<String>) ssqCache.get(SSQ_BLUES);
        HashSet<String> codess = (HashSet<String>) ssqCache.get(SSQ_CODESS);
        List<List<String>> list = new ArrayList<>();
        while (list.size() < num) {
            HashSet<String> newReds = new HashSet<>();
            while (newReds.size() < 6) {
                newReds.add(reds.get(RandomUtils.nextInt(0, reds.size())));
            }
            List<String> newSSQ = new ArrayList<>(newReds);
            Collections.sort(newSSQ);
            newSSQ.add(blues.get(RandomUtils.nextInt(0, blues.size())));
            if (repeat && codess.contains(StringUtils.join(newSSQ, ","))) {
                continue;
            }
            list.add(newSSQ);
        }
        return list;
    }

    /**
     * 同步ssq数据
     *
     * @return: void
     * @Date 2021-11-18 18:41:47
     */
    public void sycnSSQData() {
        String[] lines = SSQUtil.httpGetSSQData(lottery_ssq_url);
        if (lines == null || lines.length < 2) {
            return;
        }
        String[] infoLineArr = StringUtils.isBlank(lines[0]) ? null : lines[0].split(",");
        if (infoLineArr != null && infoLineArr.length > 4) {
            ssqCache.put(NEW_SSQ_NUM, infoLineArr[2]);
            Long time = NumberUtils.toLong(infoLineArr[3], 0);
            if (time > 0) {
                ssqCache.put(NEW_SSQ_TIME, DateFormatUtils.format(time, "yyyy-MM-dd HH:mm:ss"));
            }
        }
        List<String> reds = new ArrayList<>();
        List<String> blues = new ArrayList<>();
        HashSet<String> codess = new HashSet<>();
        for (int i = 1; i < lines.length; i++) {
            SSQDto dto = SSQDto.newSSQDto(lines[i]);
            if (dto == null) {
                continue;
            }
            if (i == 1) {
                ssqCache.put(NEW_SSQ_CODE, dto);
            }
            reds.addAll(Arrays.asList(dto.getReds()));
            blues.add(dto.getBlue1());
            codess.add(StringUtils.join(dto.toArrays()));
            ssqData.put(dto.getCode(), dto);
        }
        List<SSQDto> data = new ArrayList<>(ssqData.values());
        Collections.sort(data, (o1, o2) -> o2.getCode().compareTo(o1.getCode()));
        ssqCache.put(SSQ_SORT_LIST, data);
        ssqCache.put(SSQ_REDS, reds);
        ssqCache.put(SSQ_BLUES, blues);
        ssqCache.put(SSQ_CODESS, codess);
        Map<String, Long> redsCounts = reds.stream().collect(Collectors.groupingBy(e -> e, Collectors.counting()));
        Map<String, Long> blueCounts = blues.stream().collect(Collectors.groupingBy(e -> e, Collectors.counting()));
        ssqCache.put(SSQ_RED_COUNTS, redsCounts);
        ssqCache.put(SSQ_BLUE_COUNTS, blueCounts);
        LOGGER.info("update ssq data num={} dataLatestTime={}", ssqCache.get(NEW_SSQ_NUM), ssqCache.get(NEW_SSQ_TIME));
    }


    /**
     * 定时处理
     *
     * @return: void
     * @Author midaug
     * @Date 2021-11-09 12:07:33
     */
    @Scheduled(fixedRate = 5 * 60 * 1000)
    private void scheduledSSQ() {
        sycnSSQData();
        try {
            FileUtil.deleteFiles(cache_dir, cache_days);
        } catch (Exception e) {
        }
    }

}
