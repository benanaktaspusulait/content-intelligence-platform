package com.pompom.ruleset;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class RulesetEngineApplication {

    public static void main(String[] args) {
        SpringApplication.run(RulesetEngineApplication.class, args);
    }
}
