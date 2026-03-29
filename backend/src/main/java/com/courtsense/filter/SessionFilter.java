package com.courtsense.filter;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.UUID;

@Component
public class SessionFilter implements Filter {

    // Cookie name — this is what the browser stores and sends back on every request
    public static final String COOKIE_NAME = "COURT_SESSION";

    // 30 days in seconds
    private static final int MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest  httpReq  = (HttpServletRequest)  request;
        HttpServletResponse httpResp = (HttpServletResponse) response;

        String sessionId = readSessionCookie(httpReq);

        if (sessionId == null || sessionId.isBlank()) {
            // First visit — mint a fresh session ID
            sessionId = UUID.randomUUID().toString();
            writeSessionCookie(httpResp, sessionId);
            System.out.println("🍪 New session created: " + sessionId);
        }

        // Stash on the request so every controller can read it without touching cookies
        httpReq.setAttribute("sessionId", sessionId);

        chain.doFilter(request, response);
    }

    // ── Helpers ────────────────────────────────────────────────────────────

    private String readSessionCookie(HttpServletRequest request) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) return null;

        for (Cookie cookie : cookies) {
            if (COOKIE_NAME.equals(cookie.getName())) {
                return cookie.getValue();
            }
        }
        return null;
    }

    private void writeSessionCookie(HttpServletResponse response, String sessionId) {
        Cookie cookie = new Cookie(COOKIE_NAME, sessionId);

        // httpOnly: JS cannot read this cookie — protects against XSS
        cookie.setHttpOnly(true);

        // 30-day persistence — survives browser restarts
        cookie.setMaxAge(MAX_AGE_SECONDS);

        // Accessible across all paths on the server
        cookie.setPath("/");

        // In production behind HTTPS, set this to true.
        // Leaving false here so it works on localhost without TLS.
        cookie.setSecure(false);

        response.addCookie(cookie);
    }
}