package com.courtsense.analyzer.service;

import com.courtsense.analyzer.model.RallyPoint;
import com.courtsense.analyzer.model.Shot; // Ensure this record exists in your model package
import org.springframework.stereotype.Service;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

@Service
public class RallyAnalyzerService {

    // --- CALIBRATION CONSTANTS (Ankle-based) ---
    private static final double COURT_RIGHT_BOUNDARY = 950.0; 
    private static final double COURT_MID_LINE_Y = 540.0;
    private static final double X_MID_AXIS = 612.0;
    
    // Thresholds for Front/Back transition
    private static final double P1_BACK_THRESHOLD = 717.0; 
    private static final double P2_BACK_THRESHOLD = 484.0; 

    public List<RallyPoint> processRallyData(String filePath) {
        List<RallyPoint> cleanPoints = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {
            String line; br.readLine();
            while ((line = br.readLine()) != null) {
                String[] v = line.split(",");
                RallyPoint raw = new RallyPoint(
                    Integer.parseInt(v[0]), Integer.parseInt(v[1]),
                    Double.parseDouble(v[2]), Double.parseDouble(v[3]), Double.parseDouble(v[4])
                );
                if (raw.x() > COURT_RIGHT_BOUNDARY) continue;
                int logicalId = (raw.y() > COURT_MID_LINE_Y) ? 1 : 2;
                cleanPoints.add(new RallyPoint(raw.frame(), logicalId, raw.x(), raw.y(), raw.confidence()));
            }
        } catch (Exception e) { e.printStackTrace(); }
        return cleanPoints;
    }

    public void verifyDataQuality(List<RallyPoint> points) {
        long uniqueIds = points.stream().map(RallyPoint::rawId).distinct().count();
        System.out.println("\n--- 📝 DATA QUALITY AUDIT ---");
        System.out.println("✅ Points Analyzed: " + points.size());
        System.out.println("👥 Players Tracked: " + uniqueIds);
    }

    public void detectSmashes(List<RallyPoint> points) {
        System.out.println("\n--- 🏸 AGGRESSION REPORT ---");
        Map<Integer, Double> lastSpeeds = new HashMap<>();
        for (int i = 0; i < points.size(); i++) {
            RallyPoint curr = points.get(i);
            RallyPoint prev = findPreviousPoint(points, i, curr.rawId());
            if (prev != null) {
                double dist = Math.sqrt(Math.pow(curr.x()-prev.x(), 2) + Math.pow(curr.y()-prev.y(), 2));
                double speed = (dist / 100.0 / 0.033) * 3.6;
                double accel = speed - lastSpeeds.getOrDefault(curr.rawId(), 0.0);
                if (accel > 7.0 && speed > 13.0) {
                    System.out.printf("🔥 EXPLOSIVE BURST: Player %d | %.2f km/h | Frame %d%n", 
                                      curr.rawId(), speed, curr.frame());
                }
                lastSpeeds.put(curr.rawId(), speed);
            }
        }
    }

    /**
     * The Master Analytics Method: Combines movement and shot logic.
     */
    public void generateMatchSummary(List<RallyPoint> points) {
        Map<Integer, Double> totalDist = new HashMap<>();
        Map<Integer, Map<String, Integer>> zoneStats = new HashMap<>();
        Map<Integer, Integer> totalCount = new HashMap<>();

        for (int id : new int[]{1, 2}) {
            zoneStats.put(id, new HashMap<>());
            totalCount.put(id, 0);
        }

        // Calculate basic movement metrics
        for (int i = 0; i < points.size(); i++) {
            RallyPoint curr = points.get(i);
            RallyPoint prev = findPreviousPoint(points, i, curr.rawId());

            if (prev != null) {
                double m = Math.sqrt(Math.pow(curr.x()-prev.x(), 2) + Math.pow(curr.y()-prev.y(), 2)) / 100.0;
                totalDist.put(curr.rawId(), totalDist.getOrDefault(curr.rawId(), 0.0) + m);

                String zone = determineQuadrant(curr);
                Map<String, Integer> pZones = zoneStats.get(curr.rawId());
                pZones.put(zone, pZones.getOrDefault(zone, 0) + 1);
                totalCount.put(curr.rawId(), totalCount.get(curr.rawId()) + 1);
            }
        }

        // --- NEW: INFER SHOTS ---
        List<Shot> matchLog = inferShotSequence(points);
        
        System.out.println("\n--- 🏟️  LIVE RALLY COMMENTARY ---");
        for (Shot s : matchLog) {
            System.out.printf("[Frame %d] 🏸 Player %d hits %s from %s -> to opponent's %s%n",
                              s.frame(), s.hitterId(), s.type(), s.fromZone(), s.toZone());
        }

        printAndSaveReport(totalDist, zoneStats, totalCount, matchLog);
    }

    public List<Shot> inferShotSequence(List<RallyPoint> points) {
        List<Shot> matchLog = new ArrayList<>();
        int lastHitterId = -1;

        // We use a larger window to find the "Extreme" point of a movement
        for (int i = 10; i < points.size() - 45; i++) {
            RallyPoint curr = points.get(i);
            
            // 1. Alternating Turn Check
            if (curr.rawId() == lastHitterId) continue;

            // 2. "The Hit" Detection: Is this a local extreme in the Y-axis?
            // (A player hits at their furthest point in a lunge or clear)
            if (isExtremePoint(points, i)) {
                int hitterId = curr.rawId();
                int receiverId = (hitterId == 1) ? 2 : 1;

                // 3. "The Destination": Where is the opponent 40 frames later?
                // (It takes ~1s for a bird to travel; we look for where they finish their move)
                RallyPoint destination = findOpponentDestination(points, i, receiverId);

                if (destination != null) {
                    String from = determineQuadrant(curr);
                    String to = determineQuadrant(destination);
                    
                    // Only record if it's a valid "Game Shot"
                    String type = classifyShot(from, to);
                    matchLog.add(new Shot(curr.frame(), hitterId, from, to, type));
                    
                    lastHitterId = hitterId;
                    i += 40; // Cool-down: You can't hit another shot for at least 1.2 seconds
                }
            }
        }
        return matchLog;
    }

    /**
     * Detects if the player reached a "Turnaround" point (The Hit).
     * For P1, a hit is at Y-max (Back) or Y-min (Net). 
     * For P2, it is flipped.
     */
    private boolean isExtremePoint(List<RallyPoint> points, int idx) {
        RallyPoint p = points.get(idx);
        RallyPoint prev = points.get(idx - 3);
        RallyPoint next = points.get(idx + 3);

        if (p.rawId() == 1) { // Near Player
            boolean isBackHit = p.y() >= prev.y() && p.y() >= next.y() && p.y() > 700;
            boolean isNetHit = p.y() <= prev.y() && p.y() <= next.y() && p.y() < 600;
            return isBackHit || isNetHit;
        } else { // Far Player
            boolean isBackHit = p.y() <= prev.y() && p.y() <= next.y() && p.y() < 420;
            boolean isNetHit = p.y() >= prev.y() && p.y() >= next.y() && p.y() > 500;
            return isBackHit || isNetHit;
        }
    }

    private RallyPoint findOpponentDestination(List<RallyPoint> points, int startIdx, int targetId) {
        // Scan a window from +30 to +45 frames to find their final position
        RallyPoint best = null;
        for (int i = startIdx + 30; i < startIdx + 45; i++) {
            if (i < points.size() && points.get(i).rawId() == targetId) {
                best = points.get(i);
            }
        }
        return best;
    }

    private RallyPoint findReactionPoint(List<RallyPoint> points, int currentIndex, int targetId) {
        // Find where the opponent moves within the next ~0.5 seconds
        for (int i = currentIndex + 10; i < currentIndex + 25; i++) {
            if (i < points.size() && points.get(i).rawId() == targetId) {
                return points.get(i);
            }
        }
        return null;
    }

    private String classifyShot(String from, String to) {
        if (from.contains("BACK") && to.contains("FRONT")) return "DROP SHOT";
        if (from.contains("BACK") && to.contains("BACK")) return "CLEAR/SMASH";
        if (from.contains("FRONT") && to.contains("FRONT")) return "NET KILL/TUMBLE";
        if (from.contains("FRONT") && to.contains("BACK")) return "LOB/LIFT";
        return "DRIVE";
    }

    private String determineQuadrant(RallyPoint p) {
        if (p.rawId() == 1) { 
            boolean isBack = p.y() > 720;
            boolean isForehand = p.x() > X_MID_AXIS;
            if (isBack) return isForehand ? "BACK FOREHAND" : "BACK BACKHAND";
            return isForehand ? "FRONT FOREHAND" : "FRONT BACKHAND";
        } else { 
            boolean isBack = p.y() < 485;
            boolean isForehand = p.x() < X_MID_AXIS; 
            if (isBack) return isForehand ? "BACK FOREHAND" : "BACK BACKHAND";
            return isForehand ? "FRONT FOREHAND" : "FRONT BACKHAND";
        }
    }

    private void printAndSaveReport(Map<Integer, Double> dists, Map<Integer, Map<String, Integer>> stats, 
                                    Map<Integer, Integer> totals, List<Shot> shots) {
        System.out.println("\n--- 📊 TACTICAL SUMMARY ---");
        try (PrintWriter writer = new PrintWriter("performance_report.txt")) {
            writer.println("COURTSENSE AI: FULL ANALYTICS REPORT");
            writer.println("====================================");
            
            // Log Shot-by-Shot Commentary to file
            writer.println("\nSHOT LOG:");
            for(Shot s : shots) {
                writer.printf("[Frame %d] Player %d: %s (%s -> %s)%n", s.frame(), s.hitterId(), s.type(), s.fromZone(), s.toZone());
            }

            for (int id : new int[]{1, 2}) {
                double total = totals.getOrDefault(id, 1);
                Map<String, Integer> pStats = stats.get(id);
                String summary = String.format(
                    "\n👤 PLAYER %d stats:\n   📏 Total Run: %.2f m\n" +
                    "   🎾 BACK-FH: %.1f%% | BACK-BH: %.1f%%\n   🎾 FRNT-FH: %.1f%% | FRNT-BH: %.1f%%\n",
                    id, dists.getOrDefault(id, 0.0),
                    (pStats.getOrDefault("BACK FOREHAND", 0)*100.0/total),
                    (pStats.getOrDefault("BACK BACKHAND", 0)*100.0/total),
                    (pStats.getOrDefault("FRONT FOREHAND", 0)*100.0/total),
                    (pStats.getOrDefault("FRONT BACKHAND", 0)*100.0/total));
                System.out.print(summary + "---------------------------\n");
                writer.println(summary + "---------------------------");
            }
        } catch (Exception e) { e.printStackTrace(); }
    }

    private RallyPoint findPreviousPoint(List<RallyPoint> points, int currentIndex, int targetId) {
        for (int i = currentIndex - 1; i >= 0; i--) {
            if (points.get(i).rawId() == targetId) return points.get(i);
        }
        return null;
    }
}