package com.midaug.dream.lottery.utils;

import com.alibaba.fastjson.JSON;
import net.coobird.thumbnailator.Thumbnails;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * @className: PicUtils
 * @Description: TODO
 * @author: midaug
 * @date: 2021/11/10 17:26
 */
public class PicUtils {

    //以下是常量,按照阿里代码开发规范,不允许代码中出现魔法值
    private static final Logger LOGGER = LoggerFactory.getLogger(BaiduOcrSdkUtil.class);
    private static final Integer ZERO = 0;
    private static final Integer ONE_ZERO_TWO_FOUR = 1024;
    private static final Integer NINE_ZERO_ZERO = 900;
    private static final Integer THREE_TWO_SEVEN_FIVE = 3275;
    private static final Integer TWO_ZERO_FOUR_SEVEN = 2047;
    private static final Double ZERO_EIGHT_FIVE = 0.85;
    private static final Double ZERO_SIX = 0.6;
    private static final Double ZERO_FOUR_FOUR = 0.44;
    private static final Double ZERO_FOUR = 0.4;

    /**
     * 压缩图片文件
     */
    public static byte[] compressPicForLuban(byte[] imageBytes) {
        if (imageBytes == null || imageBytes.length < 1) {
            return imageBytes;
        }
        byte[] newBytes = {};
        try (
                ByteArrayInputStream imageIn = new ByteArrayInputStream(imageBytes);
                ByteArrayInputStream inputStream = new ByteArrayInputStream(imageBytes);
                ByteArrayOutputStream outputStream = new ByteArrayOutputStream()
        ) {

            BufferedImage image = ImageIO.read(imageIn);
            int width = image.getWidth();
            int height = image.getHeight();
            if (width == 0 || height == 0) {
                return imageBytes;
            }
            int scale = calculateSize(width, height);
            int destWidth = width / scale;
            int destHeight = height / scale;
            Thumbnails.of(inputStream)
                    .size(destWidth, destHeight)
                    .outputQuality(0.6f)
                    .toOutputStream(outputStream);
            newBytes = outputStream.toByteArray();
            LOGGER.info("图片原大小={} | 压缩后大小={} | outputQuality=0.6f   width-scale={}",
                    FileUtil.getNetFileSizeDescription(imageBytes.length),
                    FileUtil.getNetFileSizeDescription(newBytes.length),
                    1f / scale
            );
        } catch (Exception e) {
            LOGGER.error("【图片压缩】msg=图片压缩失败!", e);
            return imageBytes;
        }
        return newBytes;
    }

    /**
     * 根据图片宽高计算压缩尺寸
     *
     * @param srcWidth  图片宽度
     * @param srcHeight 图片高度
     * @return 压缩比例
     */
    private static int calculateSize(int srcWidth, int srcHeight) {
        srcWidth = srcWidth % 2 == 1 ? srcWidth + 1 : srcWidth;
        srcHeight = srcHeight % 2 == 1 ? srcHeight + 1 : srcHeight;
        int longSide = Math.max(srcWidth, srcHeight);
        int shortSide = Math.min(srcWidth, srcHeight);
        float scale = ((float) shortSide / longSide);
        if (scale <= 1 && scale > 0.5625) {
            if (longSide < 1664) {
                return 1;
            } else if (longSide >= 1664 && longSide < 4990) {
                return 2;
            } else if (longSide > 4990 && longSide < 10240) {
                return 4;
            } else {
                return longSide / 1280 == 0 ? 1 : longSide / 1280;
            }
        } else if (scale <= 0.5625 && scale > 0.5) {
            return longSide / 1280 == 0 ? 1 : longSide / 1280;
        } else {
            return (int) Math.ceil(longSide / (1280.0 / scale));
        }
    }


    /**
     * @param imageBytes:
     * @return: byte[]
     * @Date 2021-11-18 15:48:24
     */
    public static byte[] compressPicForScale(byte[] imageBytes) {
        return compressPicForScale(imageBytes, 1000);
    }

    /**
     * 根据指定大小压缩图片
     *
     * @param imageBytes  源图片字节数组
     * @param desFileSize 指定图片大小，单位kb
     * @return 压缩质量后的图片字节数组
     */
    public static byte[] compressPicForScale(byte[] imageBytes, long desFileSize) {
        if (imageBytes == null || imageBytes.length <= ZERO || imageBytes.length < desFileSize * ONE_ZERO_TWO_FOUR) {
            return imageBytes;
        }
        int srcSize = imageBytes.length;
        byte[] bytes = Arrays.copyOf(imageBytes, srcSize);
        List<Double> accuracys = new ArrayList<>();
        try {
            while (bytes.length > desFileSize * ONE_ZERO_TWO_FOUR) {
                try (
                        ByteArrayInputStream inputStream = new ByteArrayInputStream(bytes);
                        ByteArrayOutputStream outputStream = new ByteArrayOutputStream(bytes.length)
                ) {
                    double accuracy = getAccuracy(bytes.length / ONE_ZERO_TWO_FOUR);
                    accuracys.add(accuracy);
                    Thumbnails.of(inputStream)
                            .scale(accuracy)
                            .outputQuality(accuracy)
                            .toOutputStream(outputStream);
                    bytes = outputStream.toByteArray();
                } catch (Exception e) {
                    break;
                }
            }
            LOGGER.info("图片原大小={} | 压缩后大小={} | 压缩次数={}",
                    FileUtil.getNetFileSizeDescription(srcSize),
                    FileUtil.getNetFileSizeDescription(bytes.length),
                    accuracys.size() + "  " + JSON.toJSONString(accuracys)
            );
        } catch (Exception e) {
            LOGGER.error("【图片压缩】msg=图片压缩失败!", e);
        }
        return bytes;
    }

    /**
     * 自动调节精度(经验数值)
     *
     * @param size 源图片大小
     * @return 图片压缩质量比
     */
    private static double getAccuracy(long size) {
        double accuracy;
        if (size < NINE_ZERO_ZERO) {
            accuracy = ZERO_EIGHT_FIVE;
        } else if (size < TWO_ZERO_FOUR_SEVEN) {
            accuracy = ZERO_SIX;
        } else if (size < THREE_TWO_SEVEN_FIVE) {
            accuracy = ZERO_FOUR_FOUR;
        } else {
            accuracy = ZERO_FOUR;
        }
        return accuracy;
    }


    public static void main(String[] args) throws Exception {
        System.out.println(FileUtil.getNetFileSizeDescription(1000));
        byte[] bytes = FileUtils.readFileToByteArray(new File("/Users/midaug/2400.JPG"));
        FileUtils.writeByteArrayToFile(new File("/Users/midaug/444.JPG"), compressPicForLuban(bytes));
        FileUtils.writeByteArrayToFile(new File("/Users/midaug/111.JPG"), compressPicForScale(bytes));
    }
}