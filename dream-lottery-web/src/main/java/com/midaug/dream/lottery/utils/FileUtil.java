package com.midaug.dream.lottery.utils;

import org.apache.commons.io.FileUtils;
import org.apache.commons.io.filefilter.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.math.BigDecimal;
import java.text.DecimalFormat;
import java.util.Date;
import java.util.Iterator;

/**
 * @className: FileUtil
 * @Description: TODO
 * @date: 2021/11/18 19:02
 */
public class FileUtil {

    private static final Logger LOGGER = LoggerFactory.getLogger(FileUtil.class);

    /**
     * 删除指定天数前的文件
     *
     * @param dirPath:
     * @param days:
     * @return: void
     * @Date 2021-11-18 19:02:40
     */
    public static void deleteFiles(String dirPath, int days) {
        int delFNum = 0;
        int delDNum = 0;
        String dirAbsolutePath = null;
        try {
            File dir = FileUtils.getFile(dirPath);
            dirAbsolutePath = dir.getAbsolutePath();

            if (FileUtils.isEmptyDirectory(dir)) {
                return;
            }
            Date now = new Date();
            now.setTime(now.getTime() - days * 24L * 3600 * 1000);
            IOFileFilter timeFileFilter = FileFilterUtils.ageFileFilter(now, true);
            IOFileFilter fileFiles = FileFilterUtils.and(FileFileFilter.INSTANCE, timeFileFilter);
            File deleteRootFolder = new File(dirPath);
            Iterator itFile = FileUtils.iterateFiles(deleteRootFolder, fileFiles, TrueFileFilter.INSTANCE);
            while (itFile.hasNext()) {
                File file = (File) itFile.next();
                delFNum++;
                FileUtils.delete(file);
            }
            Iterator dirFile = FileUtils.iterateFilesAndDirs(deleteRootFolder, DirectoryFileFilter.DIRECTORY, TrueFileFilter.TRUE);
            while (dirFile.hasNext()) {
                File file = (File) dirFile.next();
                if (FileUtils.isEmptyDirectory(file)) {
                    delDNum++;
                    FileUtils.delete(file);
                }
            }
        } catch (Exception e) {
        } finally {
            LOGGER.info("start delete file delFNum={} delDNum={} days={} dir -> {}", delFNum, delDNum, days, dirAbsolutePath);
        }
    }

    public static String getNetFileSizeDescription(long size) {
        StringBuffer bytes = new StringBuffer();
        DecimalFormat format = new DecimalFormat("###.##");
        if (size >= 1024 * 1024 * 1024) {
            double i = (size / (1024.0 * 1024.0 * 1024.0));
            bytes.append(format.format(BigDecimal.valueOf(i))).append("GB");
        } else if (size >= 1024 * 1024) {
            double i = (size / (1024.0 * 1024.0));
            bytes.append(format.format(BigDecimal.valueOf(i))).append("MB");
        } else if (size >= 1024) {
            double i = (size / (1024.0));
            bytes.append(format.format(BigDecimal.valueOf(i))).append("KB");
        } else if (size < 1024) {
            if (size <= 0) {
                bytes.append("0B");
            } else {
                bytes.append((int) size).append("B");
            }
        }
        return bytes.toString();
    }
}
