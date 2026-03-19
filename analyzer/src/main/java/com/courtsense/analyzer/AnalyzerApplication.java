package com.courtsense.analyzer;

import com.courtsense.analyzer.service.RallyAnalyzerService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class AnalyzerApplication {

    public static void main(String[] args) {
        SpringApplication.run(AnalyzerApplication.class, args);
    }

    @Bean
    CommandLineRunner run(RallyAnalyzerService service) {
        return args -> {
            // 1. Path to your data bridge
            String path = "../rally_data.csv"; 
            
            // 2. Load and Clean the data
            var results = service.processRallyData(path);
            
            // 3. Run the Analytics Suite
            // Note: We removed calculateSpeed() because it's now inside the others!
            service.verifyDataQuality(results);
            service.detectSmashes(results);
            service.generateMatchSummary(results);
            
            System.out.println("\n🎯 Analysis Complete. Check your terminal and performance_report.txt");
        };
    }
}