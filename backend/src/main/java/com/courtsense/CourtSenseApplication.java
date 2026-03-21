package com.courtsense;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CourtSenseApplication {

    public static void main(String[] args) {
        var context = SpringApplication.run(CourtSenseApplication.class, args);
        // String dbUrl = context.getEnvironment().getProperty("DB_URL");
        // System.out.println("DEBUG: Spring sees DB_URL as: " + dbUrl);
    }

}