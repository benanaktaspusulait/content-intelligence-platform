package com.pompomhills.intelligence.security;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.time.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** Narrow owner sessions. A named owner is never an independent human assessor. */
@Component
public class CpqOwnerAccess extends OncePerRequestFilter {
  private final String ownerId; private final byte[] credentialHash;
  private final Map<String,Deque<Instant>> attempts=new LinkedHashMap<>();
  public static final String OWNER="cpq.owner", CSRF="cpq.csrf";
  public CpqOwnerAccess(@Value("${pompom.cpq-owner.id:}") String id,@Value("${pompom.cpq-owner.secret-file:}") String file) {
    ownerId=id.trim(); byte[] secret=null;
    try { if(!ownerId.isBlank() && !file.isBlank()) {String value=Files.readString(Path.of(file)).trim();if(value.length()>=32)secret=digest(value);} } catch(Exception ignored) { /* Fail closed, no secret/path logging. */ }
    credentialHash=secret;
  }
  static byte[] digest(String value) {try{return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));}catch(Exception e){throw new IllegalStateException(e);}}
  public boolean configured(){return credentialHash!=null;}
  public boolean owner(HttpServletRequest request){return configured() && ownerId.equals(request.getSession(false)==null?null:request.getSession(false).getAttribute(OWNER));}
  public String csrf(HttpServletRequest request){var session=request.getSession(true);if(session.getAttribute(CSRF)==null)session.setAttribute(CSRF,UUID.randomUUID().toString());return (String)session.getAttribute(CSRF);}
  public Map<String,Object> state(HttpServletRequest request){boolean auth=owner(request);return Map.of("configured",configured(),"authenticated",auth,"ownerId",auth?ownerId:"","csrfToken",csrf(request),"evidenceType","OWNER_DECISION","independentHumanReviewer",false);}
  public synchronized boolean login(HttpServletRequest request,String secret) {
    String key=request.getRemoteAddr();Instant now=Instant.now();
    attempts.values().forEach(q->q.removeIf(t->t.isBefore(now.minusSeconds(900))));attempts.entrySet().removeIf(e->e.getValue().isEmpty());
    if(attempts.size()>=1000 && !attempts.containsKey(key))return false;
    var queue=attempts.computeIfAbsent(key,k->new ArrayDeque<>());if(queue.size()>=5)return false;queue.add(now);
    if(!configured() || secret==null || secret.length()>1024 || !MessageDigest.isEqual(credentialHash,digest(secret)))return false;
    request.getSession(true);request.changeSessionId();request.getSession().setMaxInactiveInterval(1800);request.getSession().setAttribute(OWNER,ownerId);request.getSession().setAttribute(CSRF,UUID.randomUUID().toString());attempts.remove(key);return true;
  }
  public void logout(HttpServletRequest request){if(request.getSession(false)!=null)request.getSession(false).invalidate();}
  @Override protected boolean shouldNotFilter(HttpServletRequest r){String p=r.getRequestURI();return !p.startsWith("/api/v1/intelligence/workflow/owner-auth") && !p.contains("/cpq/") && !p.contains("/creative-prompt-quality") && !p.endsWith("/fidelity-review");}
  @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain)throws ServletException,IOException {
    response.setHeader("Cache-Control","no-store");
    String host=request.getServerName();boolean local=Set.of("localhost","127.0.0.1","::1","[::1]").contains(host);
    String remote=request.getRemoteAddr();boolean privatePeer=remote.equals("0:0:0:0:0:0:0:1")||remote.equals("::1")||remote.startsWith("127.")||remote.startsWith("172.")||remote.startsWith("192.168.")||remote.startsWith("10.");
    // Local HTTP is published on loopback only; forwarded headers do not grant TLS or identity.
    if(!request.isSecure() && !(local && privatePeer)){response.sendError(403,"Owner access requires local HTTP or direct TLS");return;}
    boolean write=!Set.of("GET","HEAD","OPTIONS").contains(request.getMethod());
    if(write && (request.getRequestURI().contains("/owner-auth") || owner(request))) {
      var session=request.getSession(false);String expected=session==null?null:(String)session.getAttribute(CSRF);String supplied=request.getHeader("X-CPQ-CSRF");
      String origin=request.getHeader("Origin");String own=(request.isSecure()?"https":"http")+"://"+request.getHeader("Host");
      if(expected==null || supplied==null || !MessageDigest.isEqual(digest(expected),digest(supplied)) || origin!=null&&!origin.equals(own)){response.sendError(403,"CSRF validation failed");return;}
    }
    if(owner(request)) {
      var wrapped=new HttpServletRequestWrapper(request) {
        @Override public Principal getUserPrincipal(){return ()->ownerId;}
        @Override public String getRemoteUser(){return ownerId;}
        @Override public boolean isUserInRole(String role){return Set.of("OWNER","PRODUCTION_OPERATOR","ARCHITECTURE_APPROVER","CREATIVE_QUALITY_ARCHITECTURE_APPROVER").contains(role);}
      };chain.doFilter(wrapped,response);
    } else chain.doFilter(request,response);
  }
}
