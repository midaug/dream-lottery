package com.midaug.dream.lottery.dto;

import lombok.Data;
import org.apache.commons.lang3.StringUtils;

/**
 * @className: SSQDto
 * @Description: SSQ实体
 * @author: midaug
 * @date: 2021/11/9 10:20
 */
@Data
public class SSQDto {

    private String code;
    private String red1;
    private String red2;
    private String red3;
    private String red4;
    private String red5;
    private String red6;
    private String blue1;
    private String bonus1;
    private String bonus2;
    private String drawDate;

    public SSQDto() {
    }

    protected SSQDto(String[] fields) {
        if (fields == null) {
            return;
        }
        if (fields.length > 0) this.code = fields[0];
        if (fields.length > 1) this.red1 = fields[1];
        if (fields.length > 2) this.red2 = fields[2];
        if (fields.length > 3) this.red3 = fields[3];
        if (fields.length > 4) this.red4 = fields[4];
        if (fields.length > 5) this.red5 = fields[5];
        if (fields.length > 6) this.red6 = fields[6];
        if (fields.length > 7) this.blue1 = fields[7];
        if (fields.length > 8) this.bonus1 = fields[8];
        if (fields.length > 9) this.bonus2 = fields[9];
        if (fields.length > 10) this.drawDate = fields[10];
    }

    public static SSQDto newSSQDto(String line) {
        if (StringUtils.isBlank(line)) {
            return null;
        }
        String[] fields = line.split(",");
        if (fields == null || fields.length < 10) {
            return null;
        }
        return new SSQDto(fields);
    }


    public String yearCode() {
        if (this.code == null) {
            return null;
        }
        return "20" + this.code;
    }

    public String[] getReds() {
        return new String[]{this.red1, this.red2, this.red3, this.red4, this.red5, this.red6};
    }

    public String[] toArrays() {
        return new String[]{this.red1, this.red2, this.red3, this.red4, this.red5, this.red6, this.blue1};
    }

    public boolean equalsCode(String code) {
        if (StringUtils.isAnyBlank(code, this.code)) {
            return false;
        }
        if (code.length() == 5) {
            return StringUtils.equals(code, this.code);
        }
        return StringUtils.equals(code, this.yearCode());
    }
}
