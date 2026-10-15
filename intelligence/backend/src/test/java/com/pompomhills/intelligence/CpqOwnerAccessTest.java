package com.pompomhills.intelligence;
import static org.assertj.core.api.Assertions.*;
import com.pompomhills.intelligence.security.CpqOwnerAccess;
import java.nio.file.*;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.*;
import jakarta.servlet.http.HttpServletRequest;

class CpqOwnerAccessTest {
 CpqOwnerAccess configured()throws Exception{Path p=Files.createTempFile("cpq-test-owner-", ".credential");Files.writeString(p,"fixture-only-secret-32-characters-minimum");p.toFile().deleteOnExit();return new CpqOwnerAccess("fixture-owner",p.toString());}
 MockHttpServletRequest request(){var r=new MockHttpServletRequest();r.setServerName("localhost");r.setRemoteAddr("127.0.0.1");r.addHeader("Host","localhost:4200");r.setRequestURI("/api/v1/intelligence/workflow/owner-auth/login");r.setMethod("POST");return r;}
 @Test void missingCredentialsFailClosed(){var access=new CpqOwnerAccess("","");assertThat(access.configured()).isFalse();assertThat(access.login(request(),"anything")).isFalse();}
 @Test void invalidCredentialsRateLimitedWithoutGrantingRoles()throws Exception{var access=configured();var r=request();for(int i=0;i<5;i++)assertThat(access.login(r,"wrong")).isFalse();assertThat(access.login(r,"fixture-only-secret-32-characters-minimum")).isFalse();assertThat(access.owner(r)).isFalse();}
 @Test void sessionOwnerIsNotHumanReviewerAndLogoutRevokes()throws Exception{var access=configured();var r=request();access.csrf(r);assertThat(access.login(r,"fixture-only-secret-32-characters-minimum")).isTrue();assertThat(r.getSession().getMaxInactiveInterval()).isEqualTo(1800);r.setMethod("GET");var received=new AtomicReference<HttpServletRequest>();access.doFilter(r,new MockHttpServletResponse(),(req,res)->received.set((HttpServletRequest)req));assertThat(received.get().getUserPrincipal().getName()).isEqualTo("fixture-owner");assertThat(received.get().isUserInRole("OWNER")).isTrue();assertThat(received.get().isUserInRole("EVIDENCE_REVIEWER")).isFalse();assertThat(received.get().isUserInRole("CREATIVE_QUALITY_REVIEWER")).isFalse();access.logout(r);assertThat(access.owner(r)).isFalse();}
 @Test void csrfAndOriginRequiredForSessionWrites()throws Exception{var access=configured();var r=request();access.csrf(r);assertThat(access.login(r,"fixture-only-secret-32-characters-minimum")).isTrue();var response=new MockHttpServletResponse();access.doFilter(r,response,(req,res)->{throw new AssertionError("Must not reach controller");});assertThat(response.getStatus()).isEqualTo(403);r.addHeader("X-CPQ-CSRF",access.csrf(r));r.addHeader("Origin","https://attacker.example");response=new MockHttpServletResponse();access.doFilter(r,response,(req,res)->{throw new AssertionError("Must not reach controller");});assertThat(response.getStatus()).isEqualTo(403);}
 @Test void validCsrfPassesButRemoteHttpIsDenied()throws Exception{var access=configured();var r=request();r.addHeader("X-CPQ-CSRF",access.csrf(r));r.addHeader("Origin","http://localhost:4200");var response=new MockHttpServletResponse();access.doFilter(r,response,(req,res)->((jakarta.servlet.http.HttpServletResponse)res).setStatus(204));assertThat(response.getStatus()).isEqualTo(204);r.setServerName("remote.example");r.setRemoteAddr("198.51.100.5");response=new MockHttpServletResponse();access.doFilter(r,response,(req,res)->{throw new AssertionError("No remote HTTP");});assertThat(response.getStatus()).isEqualTo(403);}
}
