package com.pompomhills.intelligence.security;
import jakarta.servlet.http.*;
import java.util.Map;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;
@RestController
@RequestMapping("/api/v1/intelligence/workflow/owner-auth")
public class CpqOwnerController {
  private final CpqOwnerAccess access;
  public CpqOwnerController(CpqOwnerAccess access){this.access=access;}
  @GetMapping public Map<String,Object> state(HttpServletRequest r){return access.state(r);}
  @PostMapping("/login") public Map<String,Object> login(@RequestBody Map<String,String> body,HttpServletRequest r){if(!access.login(r,body.get("credential")))throw new ResponseStatusException(UNAUTHORIZED,"Owner login unavailable, invalid or rate limited");return access.state(r);}
  @PostMapping("/logout") public Map<String,Object> logout(HttpServletRequest r){access.logout(r);return Map.of("authenticated",false);}
}
