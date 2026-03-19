package com.courtsense.analyzer.model;

public record Shot(
    int frame,
    int hitterId,
    String fromZone,
    String toZone,
    String type // <--- Ensure this is 'type'
) {}