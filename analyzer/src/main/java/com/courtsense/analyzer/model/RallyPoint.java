package com.courtsense.analyzer.model;

/**
 * A 'Record' is a transparent carrier for immutable data.
 * It automatically creates the constructor, getters, and toString().
 */
public record RallyPoint(
    int frame,
    int rawId,
    double x,
    double y,
    double confidence
) {}