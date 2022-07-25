package com.midaug.dream.lottery.dto;

import lombok.Data;

import java.util.List;

/**
 * @className: SSQDto
 * @Description: SSQ实体
 * @author: midaug
 * @date: 2021/11/9 10:20
 */
@Data
public class SSQImgOcrDto {

    private String code;
    private List<NoteDto> noteDtos;
    private SSQDto drawDto;
    private String drawDate;
    private String ocr;

    public SSQImgOcrDto() {
    }

    @Data
    public static class NoteDto extends SSQDto {
        private boolean red1f = false;
        private boolean red2f = false;
        private boolean red3f = false;
        private boolean red4f = false;
        private boolean red5f = false;
        private boolean red6f = false;
        private boolean blue1f = false;
        private String reward = "无";
        private String bonus = "0";
        private String zm;

        public NoteDto() {
        }

        public NoteDto(String[] fields) {
            super(fields);
        }
    }

}
