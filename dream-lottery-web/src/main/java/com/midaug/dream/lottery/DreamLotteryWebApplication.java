package com.midaug.dream.lottery;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication
public class DreamLotteryWebApplication {

	public static void main(String[] args) {
		SpringApplication.run(DreamLotteryWebApplication.class, args);
	}

}
