package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.*;
import com.pompomhills.intelligence.quality.QualityMlClient;
import jakarta.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;

/** Policy-scoped, ungraded machine evidence. Does not write human CPQ tables. */
@Service
public class CpqOwnerPilotService {
  static final String RECOVERY="SOURCE_CITATION_RECOVERY_V1", CITATION="CONTIGUOUS_EVENT_ORDER_V1";
  static final String SINGLE="SINGLE_SUBJECT_V1";
  public static final String POLICY="OWNER_MACHINE_PILOT_V1";
  private final JdbcClient db; private final ObjectMapper json; private final CreativePromptQualityService cpq; private final QualityMlClient ml;
  @Value("${pompom.cpq-pilot.real-enabled:false}") boolean realEnabled;
  @Value("${pompom.data-root:/tmp/pompom-data}") String dataRoot;
  public CpqOwnerPilotService(JdbcClient db,ObjectMapper json,CreativePromptQualityService cpq,QualityMlClient ml){this.db=db;this.json=json;this.cpq=cpq;this.ml=ml;}
  @SuppressWarnings("unchecked") static Map<String,Object> map(Object v){return v instanceof Map?(Map<String,Object>)v:Map.of();}
  @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(Object v){return v instanceof List?(List<Map<String,Object>>)v:List.of();}
  String encode(Object v){try{return json.copy().enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS).writeValueAsString(v);}catch(Exception e){throw new IllegalArgumentException("Invalid pilot input");}}
  Map<String,Object> read(String s){try{return json.readValue(s,new TypeReference<Map<String,Object>>(){});}catch(Exception e){throw new IllegalStateException("Invalid saved pilot");}}
  static String hash(String s){try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException(e);}}
  static UUID uuid(Object v){try{return UUID.fromString(String.valueOf(v));}catch(Exception e){throw new ResponseStatusException(BAD_REQUEST,"Exact UUID required");}}
  static double money(Object v){if(!(v instanceof Number n)||!Double.isFinite(n.doubleValue())||n.doubleValue()<=0||n.doubleValue()>20)throw new ResponseStatusException(BAD_REQUEST,"Explicit positive bounded USD budget required");return n.doubleValue();}
  String owner(HttpServletRequest r){if(r.getUserPrincipal()==null||!r.isUserInRole("OWNER"))throw new ResponseStatusException(FORBIDDEN,"Authenticated owner required; owner is not an independent human reviewer");return r.getUserPrincipal().getName();}
  public Map<String,Object> capabilities(){var out=new LinkedHashMap<String,Object>(ml.workflow("cpq-pilot/capabilities",Map.of()));out.put("realDispatchEnabled",realEnabled);out.put("policyVersion",POLICY);out.put("officialGrading","INACTIVE");return out;}
  public Map<String,Object> context(UUID analysis,UUID comparison,String candidate){return cpq.pilotSubject(analysis,comparison,candidate);}
  private Map<String,Object> snapshot(Map<String,Object> request){
    UUID analysis=uuid(request.get("analysisId"));var subjects=new ArrayList<Map<String,Object>>();subjects.add(cpq.pilotSubject(analysis,null,null));
    var selectors=rows(request.get("candidates"));if(selectors.isEmpty()||selectors.size()>3)throw new ResponseStatusException(BAD_REQUEST,"One to three exact saved candidates required");
    for(var c:selectors)subjects.add(cpq.pilotSubject(analysis,uuid(c.get("comparisonId")),String.valueOf(c.get("candidateId"))));
    String story=encode(subjects.getFirst().get("approvedStory")),settings=encode(subjects.getFirst().get("productionSettings"));
    if(subjects.stream().anyMatch(s->!story.equals(encode(s.get("approvedStory")))||!settings.equals(encode(s.get("productionSettings")))))throw new ResponseStatusException(CONFLICT,"All variants require identical source/settings");
    if(subjects.stream().map(s->s.get("promptSha256")).distinct().count()!=subjects.size())throw new ResponseStatusException(CONFLICT,"Duplicate pilot subject");
    Map<String,Object> presentation=Map.of();var file=java.nio.file.Path.of(dataRoot,"workflow","cpq-pilot-blind-manifests-v1.json");
    if(java.nio.file.Files.exists(file))try {presentation=map(map(read(java.nio.file.Files.readString(file)).get("sources")).get(subjects.getFirst().get("promptSha256")));}catch(java.io.IOException failure){throw new ResponseStatusException(CONFLICT,"Saved blind presentation unavailable");}
    if(!presentation.isEmpty()) {var ids=map(presentation.get("neutralIds"));if(subjects.stream().anyMatch(subject->!ids.containsKey(subject.get("promptSha256"))))throw new ResponseStatusException(CONFLICT,"Saved blind manifest scope differs");}
    var result=new LinkedHashMap<String,Object>();result.put("analysisId",analysis.toString());result.put("candidates",selectors);result.put("subjects",subjects);result.put("policyVersion",POLICY);result.put("blindPresentation",presentation);
    // Historical snapshots remain byte-equivalent when freshness is checked. New pilots use single-subject source reviews.
    if(!request.containsKey("subjects") || request.containsKey("sourceReviewUnit"))result.put("sourceReviewUnit",SINGLE);
    return result;
  }
  @Transactional public Map<String,Object> create(Map<String,Object> request,HttpServletRequest r){
    String actor=owner(r);if(!Boolean.TRUE.equals(request.get("confirmSourceAuthority")))throw new ResponseStatusException(BAD_REQUEST,"Explicit owner source-authority confirmation required; not independent fidelity");double budget=money(request.get("maxTotalUsd"));var prepared=new LinkedHashMap<String,Object>(request);prepared.put("sourceReviewUnit",SINGLE);var snapshot=snapshot(prepared);UUID id=UUID.randomUUID();
    db.sql("INSERT INTO cpq_owner_pilots(pilot_id,owner_principal,policy_version,scope_sha256,snapshot,total_budget_usd) VALUES(:id,:actor,:policy,:hash,CAST(:snapshot AS jsonb),:budget)").param("id",id).param("actor",actor).param("policy",POLICY).param("hash",hash(encode(snapshot))).param("snapshot",encode(snapshot)).param("budget",budget).update();
    return view(id,r);
  }
  private Map<String,Object> pilot(UUID id,HttpServletRequest r,boolean current){
    String actor=owner(r);var p=db.sql("SELECT owner_principal,snapshot::text,total_budget_usd FROM cpq_owner_pilots WHERE pilot_id=:id").param("id",id).query((rs,n)->Map.<String,Object>of("owner",rs.getString(1),"snapshot",read(rs.getString(2)),"budget",rs.getDouble(3))).optional().orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Pilot not found"));
    if(!actor.equals(p.get("owner")))throw new ResponseStatusException(FORBIDDEN,"Pilot owner differs");
    if(current && !encode(snapshot(map(p.get("snapshot")))).equals(encode(p.get("snapshot"))))throw new ResponseStatusException(CONFLICT,"Pilot source/settings/analysis is stale");return p;
  }
  public Map<String,Object> view(UUID id,HttpServletRequest r){
    var p=pilot(id,r,false);var evidence=db.sql("SELECT evidence_type,payload::text,created_at,evidence_id FROM cpq_pilot_evidence WHERE pilot_id=:id ORDER BY created_at,evidence_id").param("id",id).query((rs,n)->Map.of("evidenceId",rs.getString(4),"evidenceType",rs.getString(1),"payload",read(rs.getString(2)),"createdAt",rs.getTimestamp(3).toInstant().toString())).list();
    var requests=db.sql("SELECT request_id,slot,state,authorization_payload::text,failure FROM cpq_machine_requests WHERE pilot_id=:id ORDER BY created_at").param("id",id).query((rs,n)->{var x=new LinkedHashMap<String,Object>();x.put("requestId",rs.getString(1));x.put("slot",rs.getString(2));x.put("state",rs.getString(3));x.put("authorization",read(rs.getString(4)));x.put("failure",Objects.toString(rs.getString(5),""));return x;}).list();
    var out=new LinkedHashMap<String,Object>();out.put("pilotId",id.toString());out.put("policyVersion",POLICY);out.put("snapshot",p.get("snapshot"));out.put("evidence",evidence);out.put("requests",requests);out.put("comparison",compare(evidence));var source=sourceReview(id,map(p.get("snapshot")),requests,evidence);out.put("sourceReview",source);map(out.get("comparison")).put("sourceStatus",Boolean.TRUE.equals(source.get("complete"))?(Boolean.TRUE.equals(source.get("criticGateSatisfied"))?"COMPLETE_MACHINE_EVIDENCE_NOT_HUMAN_PASS":"REVIEW_REQUIRED"):"INCOMPLETE");out.put("officialGrading","INACTIVE");out.put("humanReviewCount",0);out.put("renderAuthorized",false);return out;
  }
  private Map<String,Object> compare(List<Map<String,Object>> evidence){
    var bySlot=new HashMap<String,Map<String,Object>>();for(var e:evidence){var payload=map(e.get("payload"));if("MACHINE_REVIEW".equals(e.get("evidenceType")))bySlot.put(String.valueOf(payload.get("slot")),map(payload.get("response")));}
    var disagreements=new ArrayList<Map<String,Object>>();var agreements=new ArrayList<Map<String,Object>>();
    var a=rows(bySlot.getOrDefault("CRITIC_A",Map.of()).get("results"));var b=rows(bySlot.getOrDefault("CRITIC_B",Map.of()).get("results"));
    for(var first:a)for(var second:b)if(Objects.equals(first.get("neutralId"),second.get("neutralId")))for(var entry:map(first.get("dimensions")).entrySet()) {
      String d=entry.getKey();var left=map(entry.getValue());var right=map(map(second.get("dimensions")).get(d));var row=Map.<String,Object>of("neutralId",first.get("neutralId"),"dimension",d,"criticA",left,"criticB",right);
      if(Objects.equals(left.get("level"),right.get("level")))agreements.add(row);else disagreements.add(row);
    }
    var shared=new ArrayList<Object>();var risks=new ArrayList<Object>();var unsupported=new ArrayList<Object>();var hypotheses=new ArrayList<Object>();
    for(var item:evidence)for(var result:rows(map(map(item.get("payload")).get("response")).get("results"))) {
      risks.addAll((List<?>)result.getOrDefault("productionRisks",List.of()));unsupported.addAll((List<?>)result.getOrDefault("unsupportedClaims",List.of()));hypotheses.addAll((List<?>)result.getOrDefault("improvementHypotheses",List.of()));
    }
    for(var left:a)for(var right:b)if(Objects.equals(left.get("neutralId"),right.get("neutralId")))for(String dimension:map(left.get("dimensions")).keySet()) {
      var first=map(map(left.get("dimensions")).get(dimension));var second=map(map(right.get("dimensions")).get(dimension));
      for(Object weakness:(List<?>)first.getOrDefault("weaknesses",List.of()))if(((List<?>)second.getOrDefault("weaknesses",List.of())).contains(weakness))shared.add(Map.of("neutralId",left.get("neutralId"),"dimension",dimension,"weakness",weakness));
    }
    var out=new LinkedHashMap<String,Object>();out.put("agreements",agreements);out.put("disagreements",disagreements);out.put("sharedWeaknesses",shared);out.put("productionRisks",risks);out.put("unsupportedClaims",unsupported);out.put("improvementHypotheses",hypotheses);out.put("resolution","OWNER_REVIEW_REQUIRED_NO_AVERAGING");out.put("materialImprovement","INSUFFICIENT_EVIDENCE");out.put("sourceStatus",bySlot.containsKey("SOURCE_FIDELITY")?"SEE_MACHINE_EVIDENCE_NOT_HUMAN_PASS":"NOT_EXECUTED");
    var first=bySlot.getOrDefault("CRITIC_A",Map.of());var second=bySlot.getOrDefault("CRITIC_B",Map.of());out.put("independenceLimitations",!first.isEmpty()&&!second.isEmpty()&&Objects.equals(first.get("provider"),second.get("provider"))?List.of("Shared provider/model-family bias may remain; two executions are not two independent humans"):List.of("Machine independence does not establish human calibration"));return out;
  }
  Map<String,Object> input(Map<String,Object> saved,String slot){
    var subjects=rows(saved.get("subjects"));var sorted=new ArrayList<>(subjects);String seed=hash(encode(saved));sorted.sort(Comparator.comparing(s->hash(seed+"|"+s.get("promptSha256"))));
    var packets=new ArrayList<Map<String,Object>>();int n=0;
    for(var subject:sorted){var packet=new LinkedHashMap<String,Object>();String fallback="Q0"+(++n);packet.put("neutralId",map(map(saved.get("blindPresentation")).get("neutralIds")).getOrDefault(subject.get("promptSha256"),fallback));packet.put("prompt",subject.get("promptText"));packet.put("promptSha256",subject.get("promptSha256"));packet.put("productionSettings",subject.get("productionSettings"));
      if(slot.equals("SOURCE_FIDELITY")){packet.put("approvedStory",map(subject.get("approvedStory")).get("text"));packet.put("originalPrompt",subject.get("originalPrompt"));packet.put("changedBeats",subject.get("changedBeats"));}
      packets.add(packet);
    }
    Object savedOrder=map(map(saved.get("blindPresentation")).get("orders")).get(slot);
    if(savedOrder instanceof List<?> order)packets.sort(Comparator.comparingInt(packet->order.indexOf(packet.get("neutralId"))));
    else packets.sort(Comparator.comparing(s->hash(seed+"|"+slot+"|"+s.get("neutralId"))));
    return Map.of("policyVersion",POLICY,"rubricVersion",CreativePromptQualityService.RUBRIC,"purpose",slot.equals("SOURCE_FIDELITY")?"SOURCE_FIDELITY":"CREATIVE_CRITIC","packets",packets,"evidenceType","MACHINE_REVIEW","evidenceScope","TEXT_ONLY");
  }
  Map<String,Object> sourceInput(Map<String,Object> saved,String sha) {
    var subject=rows(saved.get("subjects")).stream().filter(x->Objects.equals(sha,x.get("promptSha256"))).findFirst().orElseThrow(()->new ResponseStatusException(CONFLICT,"Exact pilot source subject required"));
    var legacy=input(saved,"SOURCE_FIDELITY");var packet=new LinkedHashMap<String,Object>(rows(legacy.get("packets")).stream().filter(x->Objects.equals(sha,x.get("promptSha256"))).findFirst().orElseThrow());
    packet.remove("originalPrompt");var binding=new LinkedHashMap<String,Object>();
    for(String key:List.of("promptSha256","approvedStorySha256","productionSettingsSha256","sourceIdentity"))binding.put(key,subject.get(key));
    for(String key:List.of("storyId","revision","approvalRecordId"))binding.put(key,map(subject.get("approvedStory")).get(key));
    packet.put("sourceBinding",binding);
    String story=String.valueOf(packet.get("approvedStory"));var events=new ArrayList<Map<String,Object>>();
    var matcher=java.util.regex.Pattern.compile("\\S[\\s\\S]*?(?:[.!?](?=\\s|$)|$)").matcher(story);
    while(matcher.find())events.add(Map.of("eventId",String.format("event_%02d",events.size()+1),"sourceStart",story.codePointCount(0,matcher.start()),"sourceEnd",story.codePointCount(0,matcher.end())));
    packet.put("requiredEvents",events);
    packet.put("changedBeats",rows(packet.get("changedBeats")).stream().map(b->Map.of("beatId",b.get("beatId"),"originalExecution",b.getOrDefault("originalExecution",b.getOrDefault("originalInstruction","")),"newExecution",b.getOrDefault("newExecution",b.getOrDefault("revisedInstruction","")))).toList());
    var result=new LinkedHashMap<String,Object>(legacy);result.put("evaluationUnit",SINGLE);result.put("packets",List.of(packet));return result;
  }
  Map<String,Object> sourceReview(UUID id,Map<String,Object> saved,List<? extends Map<String,Object>> requests,List<Map<String,Object>> evidence) {
    var bindings=rows(input(saved,"SOURCE_FIDELITY").get("packets"));var statuses=new ArrayList<Map<String,Object>>();var missing=new ArrayList<Object>();int valid=0,conflicts=0,review=0;
    for(var packet:bindings){String sha=String.valueOf(packet.get("promptSha256"));Object neutral=packet.get("neutralId");Map<String,Object> result=Map.of();
      for(var e:evidence){var payload=map(e.get("payload"));if(!"MACHINE_REVIEW".equals(e.get("evidenceType"))||!"SOURCE_FIDELITY".equals(payload.get("slot")))continue;
        var req=requests.stream().filter(q->Objects.equals(q.get("requestId"),payload.get("requestId"))&&("COMPLETED".equals(q.get("state")) || ("FAILED_OR_AMBIGUOUS".equals(q.get("state")) && RECOVERY.equals(payload.get("recoveryPolicyVersion"))))).findFirst();
        if(req.isEmpty() || !Objects.equals(payload.get("sourceStorySha256"),rows(saved.get("subjects")).getFirst().get("approvedStorySha256")) || !Objects.equals(payload.get("productionSettingsSha256"),rows(saved.get("subjects")).getFirst().get("productionSettingsSha256")))continue;
        if(rows(payload.get("promptBindings")).stream().noneMatch(b->Objects.equals(b.get("neutralId"),neutral)&&Objects.equals(b.get("promptSha256"),sha)))continue;
        var persistedInput=db.sql("SELECT input::text,input_sha256 FROM cpq_machine_requests WHERE request_id=:request AND pilot_id=:pilot").param("request",uuid(payload.get("requestId"))).param("pilot",id).query((rs,n)->Map.of("input",read(rs.getString(1)),"hash",rs.getString(2))).single();
        if(!Objects.equals(persistedInput.get("hash"),payload.get("inputSha256")) || !Objects.equals(hash(encode(map(persistedInput.get("input")))),persistedInput.get("hash")))continue;
        try{if("FAILED_OR_AMBIGUOUS".equals(req.get().get("state"))){var row=recoveryRow(id,uuid(payload.get("requestId")));var proof=recoveryProof(id,uuid(payload.get("requestId")),saved,row);if(!Objects.equals(proof,payload.get("recoveryProof")) || !Boolean.TRUE.equals(map(payload.get("authorization")).get("authorizeOfflineRevalidation")) || !Boolean.TRUE.equals(map(payload.get("authorization")).get("confirmNoInferenceNoApproval")))continue;validateRecovered(row,proof,map(payload.get("response")));}else validateSingleSource(map(persistedInput.get("input")),map(payload.get("response")));}catch(RuntimeException invalid){continue;}
        for(var found:rows(map(payload.get("response")).get("results")))if(Objects.equals(found.get("neutralId"),neutral))result=found;
      }
      var out=new LinkedHashMap<String,Object>();out.put("neutralId",neutral);out.put("promptSha256",sha);String state="NOT_EXECUTED";
      for(var req:requests)if("SOURCE_FIDELITY".equals(req.get("slot")) && (!map(req.get("authorization")).containsKey("subjectPromptSha256") || Objects.equals(map(req.get("authorization")).get("subjectPromptSha256"),sha)))state="DISPATCHING".equals(req.get("state"))?"RUNNING":String.valueOf(req.get("state"));
      if(!result.isEmpty()){valid++;boolean conflict=Boolean.TRUE.equals(result.get("conflict"))||!((List<?>)result.getOrDefault("omissions",List.of())).isEmpty()||!((List<?>)result.getOrDefault("additions",List.of())).isEmpty();
        boolean needsReview=conflict||!"PASS".equals(result.get("decision"))||result.containsKey("validationNotice")||!((List<?>)result.getOrDefault("unsupportedClaims",List.of())).isEmpty();
        if(conflict)conflicts++;if(needsReview)review++;state=needsReview?"REVIEW_REQUIRED":"COMPLETED_WITH_EVIDENCE";out.put("semanticVerdict",result.get("decision"));
      }else {missing.add(neutral);if("COMPLETED".equals(state))state="REVIEW_REQUIRED";}
      out.put("status",state);out.put("hasValidatedEvidence",!result.isEmpty());statuses.add(out);
    }
    boolean complete=valid==bindings.size();return Map.of("subjects",statuses,"requiredSubjects",bindings.size(),"validatedSubjects",valid,"conflictSubjects",conflicts,"manualAdjudicationSubjects",review,"missingSubjectIds",missing,"complete",complete,"criticGateSatisfied",complete && (SINGLE.equals(saved.get("sourceReviewUnit"))?review==0:true),"evidenceType","MACHINE_REVIEW");
  }
  // Match the ML CONTIGUOUS_EVENT_ORDER_V1 contract; ranges never replace single-event coverage.
  List<Object> citationEventRange(Map<String,Object> packet,Map<String,Object> mapping) {
    String source=String.valueOf(packet.get("approvedStory")),quote=String.valueOf(mapping.getOrDefault("sourceQuote",""));
    var events=rows(packet.get("requiredEvents"));int anchor=-1;
    for(int i=0;i<events.size();i++)if(Objects.equals(events.get(i).get("eventId"),mapping.get("eventId")))anchor=i;
    if(anchor<0 || quote.isEmpty())throw new IllegalArgumentException("Exact required source-event citation required");
    var event=events.get(anchor);int start=source.offsetByCodePoints(0,((Number)event.get("sourceStart")).intValue()),end=source.offsetByCodePoints(0,((Number)event.get("sourceEnd")).intValue());
    if(source.substring(start,end).contains(quote))return List.of(event.get("eventId"));
    var matches=new ArrayList<List<Object>>();
    if("EVENT_ORDER".equals(mapping.get("anchor")))for(int first=0;first<events.size();first++)for(int count=2;count<=3;count++){
      int last=first+count-1;if(last>=events.size() || anchor<first || anchor>last || count==events.size())continue;
      start=source.offsetByCodePoints(0,((Number)events.get(first).get("sourceStart")).intValue());end=source.offsetByCodePoints(0,((Number)events.get(last).get("sourceEnd")).intValue());
      if(source.substring(start,end).equals(quote))matches.add(events.subList(first,last+1).stream().map(e->e.get("eventId")).toList());
    }
    if(matches.size()==1)return matches.getFirst();
    throw new IllegalArgumentException("Exact required source-event citation required");
  }
  void validateSingleSource(Map<String,Object> input,Map<String,Object> response) {
    if(!SINGLE.equals(input.get("evaluationUnit")))return;
    if(!(response.get("rawResponse") instanceof String raw) || raw.isBlank() || !"COMPLETE".equals(response.get("usageAccountingStatus")) || !"stop".equals(map(response.get("providerMetadata")).get("finishReason")))throw new IllegalArgumentException("Complete visible source response and accounting required");
    if(rows(input.get("packets")).size()!=1 || rows(response.get("results")).size()!=1)throw new IllegalArgumentException("Exactly one source result required");
    var packet=rows(input.get("packets")).getFirst();var result=rows(response.get("results")).getFirst();
    if(!Objects.equals(packet.get("sourceBinding"),result.get("sourceBinding")))throw new IllegalArgumentException("Exact response source binding required");
    var mappings=rows(result.get("mappings"));var anchors=new HashSet<Object>();var events=new HashSet<Object>();var beats=new HashSet<Object>();
    String source=String.valueOf(packet.get("approvedStory")),prompt=String.valueOf(packet.get("prompt"));boolean uncertain=false;
    for(var m:mappings){anchors.add(m.get("anchor"));beats.add(m.get("beatId"));String sq=String.valueOf(m.getOrDefault("sourceQuote","")),pq=String.valueOf(m.getOrDefault("promptQuote",""));
      var event=rows(packet.get("requiredEvents")).stream().filter(e->Objects.equals(e.get("eventId"),m.get("eventId"))).findFirst().orElseThrow(()->new IllegalArgumentException("Unknown source event"));
      int start=source.offsetByCodePoints(0,((Number)event.get("sourceStart")).intValue()),end=source.offsetByCodePoints(0,((Number)event.get("sourceEnd")).intValue());
      citationEventRange(packet,m);
      if(!Set.of("PASS","FAIL","UNKNOWN").contains(m.get("consistency")) || sq.isEmpty() || !prompt.contains(pq) || (pq.isEmpty()&&"PASS".equals(m.get("consistency"))))throw new IllegalArgumentException("Exact evidence-backed mapping required");
      if(source.substring(start,end).equals(sq))events.add(m.get("eventId"));
      uncertain |= !"PASS".equals(m.get("consistency"));
    }
    if(rows(packet.get("changedBeats")).stream().anyMatch(b->mappings.stream().noneMatch(m->Objects.equals(m.get("beatId"),b.get("beatId"))&&Objects.equals(m.get("promptQuote"),b.get("newExecution")))))throw new IllegalArgumentException("Exact changed-beat execution evidence required");
    if(!anchors.equals(Set.of("CHARACTER_IDENTITY","APPROVED_EVENTS","EVENT_ORDER","PHYSICAL_RULE","TEMPORAL_CONSTRAINTS","REQUIRED_ENDING")) || !events.equals(rows(packet.get("requiredEvents")).stream().map(e->e.get("eventId")).collect(java.util.stream.Collectors.toSet())) || !beats.containsAll(rows(packet.get("changedBeats")).stream().map(b->b.get("beatId")).toList()))throw new IllegalArgumentException("Complete source evidence required");
    if(!Set.of("PASS","FAIL","UNKNOWN").contains(result.get("decision")) || String.valueOf(result.getOrDefault("rationale","")).trim().length()<20 || String.valueOf(result.getOrDefault("uncertainty","")).isBlank() || !(result.get("omissions") instanceof List) || !(result.get("additions") instanceof List) || !(result.get("conflict") instanceof Boolean) || !(result.get("productionRisks") instanceof List))throw new IllegalArgumentException("Complete semantic evidence required");
    if("PASS".equals(result.get("decision")) && (uncertain || Boolean.TRUE.equals(result.get("conflict")) || !((List<?>)result.get("omissions")).isEmpty() || !((List<?>)result.get("additions")).isEmpty() || !((List<?>)result.getOrDefault("unsupportedClaims",List.of())).isEmpty()))throw new IllegalArgumentException("Unsupported semantic PASS");
  }
  private Map<String,Object> recoveryRow(UUID id,UUID request) {
    return db.sql("SELECT slot,state,input::text,input_sha256,response::text,authorization_payload::text FROM cpq_machine_requests WHERE pilot_id=:id AND request_id=:request").param("id",id).param("request",request).query((rs,n)->Map.<String,Object>of("slot",rs.getString(1),"state",rs.getString(2),"input",read(rs.getString(3)),"inputSha256",rs.getString(4),"response",read(Objects.toString(rs.getString(5),"{}")),"authorization",read(rs.getString(6)))).optional().orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Saved request not found"));
  }
  private Map<String,Object> recoveryProof(UUID id,UUID request,Map<String,Object> saved,Map<String,Object> row) {
    var input=map(row.get("input"));var response=map(row.get("response"));var packets=rows(input.get("packets"));
    if(!"SOURCE_FIDELITY".equals(row.get("slot")) || !"FAILED_OR_AMBIGUOUS".equals(row.get("state")) || !SINGLE.equals(input.get("evaluationUnit")) || packets.size()!=1 || !Objects.equals(hash(encode(input)),row.get("inputSha256")))throw new ResponseStatusException(CONFLICT,"Only an immutable single-source contract failure is eligible");
    var packet=packets.getFirst();
    if(!encode(sourceInput(saved,String.valueOf(packet.get("promptSha256")))).equals(encode(input)))throw new ResponseStatusException(CONFLICT,"Current prompt/source/settings binding differs");
    if(!(response.get("rawResponse") instanceof String raw) || raw.isBlank())throw new ResponseStatusException(CONFLICT,"Retained visible provider output required");
    var proof=new LinkedHashMap<String,Object>();proof.put("recoveryPolicyVersion",RECOVERY);proof.put("citationContractVersion",CITATION);proof.put("pilotId",id.toString());proof.put("requestId",request.toString());proof.put("inputSha256",row.get("inputSha256"));proof.put("originalResponseSha256",hash(encode(response)));proof.put("rawResponseSha256",hash(raw));proof.put("providerResponseId",map(response.get("providerMetadata")).get("requestId"));proof.put("sourceBinding",packet.get("sourceBinding"));return proof;
  }
  private Map<String,Object> revalidateRecovery(Map<String,Object> row,Map<String,Object> proof) {
    var body=new LinkedHashMap<String,Object>(proof);body.put("input",row.get("input"));body.put("savedResponse",row.get("response"));body.put("originalAuthorization",row.get("authorization"));
    var response=ml.workflow("cpq-pilot/revalidate-source",body);validateRecovered(row,proof,response);return response;
  }
  private void validateRecovered(Map<String,Object> row,Map<String,Object> proof,Map<String,Object> response) {
    var original=map(row.get("response"));String raw=String.valueOf(original.get("rawResponse"));
    if(!"OFFLINE_REVALIDATED".equals(response.get("executionStatus")) || !"RECOVERED_MACHINE_EVIDENCE".equals(response.get("evidenceProvenance")) || !RECOVERY.equals(response.get("recoveryPolicyVersion")) || !CITATION.equals(response.get("citationContractVersion")) || !Boolean.FALSE.equals(response.get("newInference")) || !(response.get("newInferenceCostUsd") instanceof Number cost) || cost.doubleValue()!=0 || !Objects.equals(raw,response.get("rawResponse")) || !Objects.equals(proof.get("rawResponseSha256"),response.get("rawResponseSha256")) || !Objects.equals(proof.get("inputSha256"),response.get("inputSha256")))throw new IllegalArgumentException("Exact offline recovery provenance required");
    for(String key:List.of("requestId","provider","model","providerMetadata","usage","usageAccountingStatus","costUsd"))if(!Objects.equals(original.get(key),response.get(key)))throw new IllegalArgumentException("Original provider evidence must remain unchanged");
    var rawResults=rows(read(raw).get("results"));var results=rows(response.get("results"));
    if(rawResults.size()!=1 || results.size()!=1)throw new IllegalArgumentException("One unchanged model decision required");
    var semantic=new LinkedHashMap<String,Object>(results.getFirst());for(String key:List.of("validationNotice","unsupportedClaims","evidenceScope"))semantic.remove(key);
    if(!encode(rawResults.getFirst()).equals(encode(semantic)))throw new IllegalArgumentException("Model decision and findings must remain unchanged");
    var input=map(row.get("input"));var packet=rows(input.get("packets")).getFirst();var auth=map(row.get("authorization"));var meta=map(original.get("providerMetadata"));var usage=map(original.get("usage"));
    if(!"FAILED_OR_AMBIGUOUS".equals(original.get("executionStatus")) || !"PROVIDER_OR_RESPONSE_CONTRACT_FAILED".equals(original.get("failureCategory")) || !rows(original.get("results")).isEmpty() || !"COMPLETED".equals(meta.get("apiStatus")) || !Objects.equals(meta.get("requestId"),proof.get("providerResponseId")) || !Objects.equals(original.get("model"),auth.get("model")) || !Objects.equals(meta.get("model"),auth.get("model")) || !Objects.equals(original.get("provider"),auth.get("provider")) || !Objects.equals(auth.get("subjectPromptSha256"),packet.get("promptSha256")) || !(original.get("costUsd") instanceof Number actual) || !Double.isFinite(actual.doubleValue()) || actual.doubleValue()<0 || actual.doubleValue()>((Number)auth.get("maxCostUsd")).doubleValue() || !(usage.get("completion_tokens") instanceof Number tokens) || tokens.longValue()<0 || tokens.longValue()>((Number)auth.get("maxOutputTokens")).longValue())throw new IllegalArgumentException("Completed bounded original inference required");
    boolean corrected=false;String source=String.valueOf(packet.get("approvedStory"));
    for(var mapping:rows(rawResults.getFirst().get("mappings"))){var event=rows(packet.get("requiredEvents")).stream().filter(e->Objects.equals(e.get("eventId"),mapping.get("eventId"))).findFirst().orElseThrow();String span=source.substring(source.offsetByCodePoints(0,((Number)event.get("sourceStart")).intValue()),source.offsetByCodePoints(0,((Number)event.get("sourceEnd")).intValue()));if(!span.contains(String.valueOf(mapping.get("sourceQuote")))){if(citationEventRange(packet,mapping).size()<2)throw new IllegalArgumentException("Uncorrected citation failure");corrected=true;}}
    if(!corrected)throw new IllegalArgumentException("Demonstrated corrected citation defect required");
    validateSingleSource(input,response);
  }
  public Map<String,Object> recoveryPreview(UUID id,UUID request,HttpServletRequest r) {
    var saved=map(pilot(id,r,true).get("snapshot"));var row=recoveryRow(id,request);var proof=recoveryProof(id,request,saved,row);var response=revalidateRecovery(row,proof);
    return Map.of("eligible",true,"persisted",false,"expectedAuthorization",proof,"response",response,"newInference",false,"requiresExplicitOwnerAuthorization",true);
  }
  @Transactional public Map<String,Object> recoverSource(UUID id,UUID request,Map<String,Object> body,HttpServletRequest r) {
    var saved=map(pilot(id,r,true).get("snapshot"));
    if(!Boolean.TRUE.equals(body.get("authorizeOfflineRevalidation")) || !Boolean.TRUE.equals(body.get("confirmNoInferenceNoApproval")))throw new ResponseStatusException(BAD_REQUEST,"Explicit offline evidence recovery authorization required; no inference or prompt approval");
    db.sql("SELECT pilot_id FROM cpq_owner_pilots WHERE pilot_id=:id FOR UPDATE").param("id",id).query(UUID.class).single();
    var row=recoveryRow(id,request);var proof=recoveryProof(id,request,saved,row);
    for(var entry:proof.entrySet())if(!Objects.equals(entry.getValue(),body.get(entry.getKey())))throw new ResponseStatusException(CONFLICT,"Exact recovery authorization binding differs: "+entry.getKey());
    var existing=db.sql("SELECT payload::text FROM cpq_pilot_evidence WHERE request_id=:request").param("request",request).query(String.class).optional();
    if(existing.isPresent()){var prior=read(existing.get());if(!Objects.equals(prior.get("recoveryProof"),proof))throw new ResponseStatusException(CONFLICT,"Existing evidence provenance differs");validateRecovered(row,proof,map(prior.get("response")));return view(id,r);}
    var response=revalidateRecovery(row,proof);var packet=rows(map(row.get("input")).get("packets")).getFirst();var binding=map(packet.get("sourceBinding"));
    var evidence=new LinkedHashMap<String,Object>();evidence.put("slot","SOURCE_FIDELITY");evidence.put("requestId",request.toString());evidence.put("inputSha256",row.get("inputSha256"));evidence.put("response",response);evidence.put("evidenceProvenance","RECOVERED_MACHINE_EVIDENCE");evidence.put("recoveryProof",proof);evidence.put("recoveryPolicyVersion",RECOVERY);evidence.put("authorizedBy",owner(r));evidence.put("authorization",body);evidence.put("sourceStorySha256",binding.get("approvedStorySha256"));evidence.put("productionSettingsSha256",binding.get("productionSettingsSha256"));evidence.put("promptBindings",List.of(Map.of("neutralId",packet.get("neutralId"),"promptSha256",packet.get("promptSha256"))));evidence.put("newInference",false);evidence.put("newInferenceCostUsd",0);evidence.put("evidenceScope","TEXT_ONLY");
    db.sql("INSERT INTO cpq_pilot_evidence(evidence_id,pilot_id,request_id,evidence_type,actor,payload) VALUES(:evidence,:pilot,:request,'MACHINE_REVIEW',:owner,CAST(:payload AS jsonb))").param("evidence",UUID.randomUUID()).param("pilot",id).param("request",request).param("owner",owner(r)).param("payload",encode(evidence)).update();return view(id,r);
  }
  boolean sourceGate(UUID id,HttpServletRequest r){return Boolean.TRUE.equals(map(view(id,r).get("sourceReview")).get("criticGateSatisfied"));}
  @Transactional public Map<String,Object> authorize(UUID id,Map<String,Object> body,HttpServletRequest r){
    var p=pilot(id,r,true);db.sql("SELECT pilot_id FROM cpq_owner_pilots WHERE pilot_id=:id FOR UPDATE").param("id",id).query(UUID.class).single();
    String slot=String.valueOf(body.get("slot"));if(!Set.of("SOURCE_FIDELITY","CRITIC_A","CRITIC_B").contains(slot))throw new ResponseStatusException(BAD_REQUEST,"Exact review slot required");
    if(!Boolean.TRUE.equals(body.get("authorizePaidInference"))||!Boolean.FALSE.equals(body.get("automaticRetries")))throw new ResponseStatusException(BAD_REQUEST,"Explicit single paid dispatch authorization with retries disabled required");
    String key=String.valueOf(body.getOrDefault("idempotencyKey",""));if(key.length()<16||key.length()>100)throw new ResponseStatusException(BAD_REQUEST,"Durable idempotency key required");
    var saved=map(p.get("snapshot"));boolean scoped=slot.equals("SOURCE_FIDELITY") && SINGLE.equals(saved.get("sourceReviewUnit"));String subject=scoped?String.valueOf(body.getOrDefault("subjectPromptSha256","")):"";
    if(scoped && rows(saved.get("subjects")).stream().noneMatch(x->Objects.equals(subject,x.get("promptSha256"))))throw new ResponseStatusException(CONFLICT,"Exact pilot subjectPromptSha256 required");
    if(!slot.equals("SOURCE_FIDELITY") && body.containsKey("subjectPromptSha256"))throw new ResponseStatusException(BAD_REQUEST,"Critics evaluate the complete pilot; no subject scope allowed");
    var caps=capabilities();var profiles=map(caps.get("profiles"));String identity=String.valueOf(body.get("profileId"));var profile=map(profiles.get(identity));
    if(slot.equals("SOURCE_FIDELITY")) {
      var source=map(map(caps.get("sourceFidelityConfiguration")).get(identity));
      String effort=String.valueOf(source.getOrDefault("reasoningEffort",""));
      if(effort.isBlank() || !((List<?>)source.getOrDefault("supportedReasoningEfforts",List.of())).contains(effort))throw new ResponseStatusException(CONFLICT,"Verified source-fidelity reasoning configuration required");
      if(body.containsKey("reasoningEffort")&&!Objects.equals(body.get("reasoningEffort"),effort))throw new ResponseStatusException(CONFLICT,"Source reasoning effort differs from the current configuration; fresh exact authorization required");
      body=new LinkedHashMap<>(body);body.put("reasoningEffort",effort);
    }
    var existing=db.sql("SELECT authorization_payload::text FROM cpq_machine_requests WHERE pilot_id=:id AND idempotency_key=:key").param("id",id).param("key",key).query(String.class).optional();
    if(existing.isPresent()){if(!encode(read(existing.get())).equals(encode(body)))throw new ResponseStatusException(CONFLICT,"Idempotency key reused with different authorization");return view(id,r);}
    if(db.sql("SELECT count(*) FROM cpq_machine_requests WHERE pilot_id=:id AND slot=:slot AND (subject_prompt_sha256=:subject OR subject_prompt_sha256 IS NULL OR :subject='')").param("id",id).param("slot",slot).param("subject",subject).query(Integer.class).single()>0)throw new ResponseStatusException(CONFLICT,"Review slot already has an immutable authorization; inspect saved request instead of retrying");
    if(!Boolean.TRUE.equals(profile.get("configured"))||!Objects.equals(body.get("provider"),profile.get("provider"))||!Objects.equals(body.get("model"),profile.get("model")))throw new ResponseStatusException(CONFLICT,"Exact configured provider/model required; no fallback");
    int tokens=body.get("maxOutputTokens") instanceof Number n?n.intValue():0;if(tokens<256||tokens>4000)throw new ResponseStatusException(BAD_REQUEST,"Output limit must be 256–4000");
    double cap=money(body.get("maxCostUsd"));var input=scoped?sourceInput(saved,subject):input(saved,slot);int bytes=encode(input).getBytes(StandardCharsets.UTF_8).length+12000;
    double bound=bytes*((Number)profile.get("inputUsdPerMillion")).doubleValue()/1e6+tokens*((Number)profile.get("outputUsdPerMillion")).doubleValue()/1e6;
    if(bound>cap)throw new ResponseStatusException(CONFLICT,"Per-call budget below conservative input/schema/output bound");
    Double reserved=db.sql("SELECT coalesce(sum(reserved_usd),0) FROM cpq_machine_requests WHERE pilot_id=:id").param("id",id).query(Double.class).single();if(reserved+cap>((Number)p.get("budget")).doubleValue()+1e-9)throw new ResponseStatusException(CONFLICT,"Total pilot budget exceeded");
    if(slot.equals("SOURCE_FIDELITY"))for(var s:rows(saved.get("subjects")))if((!scoped || subject.equals(s.get("promptSha256"))) && "OPTIMIZATION_CANDIDATE".equals(s.get("subjectType"))){var generation=map(s.get("generationIdentity"));if(String.valueOf(generation.getOrDefault("provider","")).isBlank()||String.valueOf(generation.getOrDefault("model","")).isBlank())throw new ResponseStatusException(CONFLICT,"Generator identity unavailable for independent source check");if(Objects.equals(generation.get("provider"),profile.get("provider"))&&Objects.equals(generation.get("model"),profile.get("model")))throw new ResponseStatusException(CONFLICT,"Source checker cannot be candidate generator");}
    UUID request=UUID.randomUUID();db.sql("INSERT INTO cpq_machine_requests(request_id,pilot_id,slot,idempotency_key,authorized_by,authorization_payload,input_sha256,state,reserved_usd,input,subject_prompt_sha256) VALUES(:request,:id,:slot,:key,:owner,CAST(:authorization AS jsonb),:hash,'AUTHORIZED',:cap,CAST(:input AS jsonb),NULLIF(:subject,''))").param("request",request).param("id",id).param("slot",slot).param("key",key).param("owner",owner(r)).param("authorization",encode(body)).param("hash",hash(encode(input))).param("cap",cap).param("subject",subject).param("input",encode(input)).update();return view(id,r);
  }
  // Intentionally not @Transactional: durable CAS commits BEFORE transport. Ambiguity never retries.
  public Map<String,Object> execute(UUID pilotId,UUID requestId,HttpServletRequest r){
    pilot(pilotId,r,true);if(!realEnabled)throw new ResponseStatusException(FORBIDDEN,"Real dispatch disabled; separate owner/provider authorization and server configuration required");
    var row=db.sql("SELECT slot,state,input::text,authorization_payload::text FROM cpq_machine_requests WHERE request_id=:request AND pilot_id=:pilot").param("request",requestId).param("pilot",pilotId).query((rs,n)->Map.of("slot",rs.getString(1),"state",rs.getString(2),"input",read(rs.getString(3)),"authorization",read(rs.getString(4)))).optional().orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Authorized request not found"));
    if(!"AUTHORIZED".equals(row.get("state")))return view(pilotId,r);
    if(!"SOURCE_FIDELITY".equals(row.get("slot")) && !sourceGate(pilotId,r))throw new ResponseStatusException(CONFLICT,"Separate source stage must complete first");
    if(db.sql("SELECT count(*) FROM cpq_machine_requests WHERE pilot_id=:id AND (state='DISPATCHING' OR (state='FAILED_OR_AMBIGUOUS' AND (slot<>'SOURCE_FIDELITY' OR :source=false)))").param("id",pilotId).param("source","SOURCE_FIDELITY".equals(row.get("slot"))).query(Integer.class).single()>0)throw new ResponseStatusException(CONFLICT,"Unresolved dispatch/failure blocks subsequent calls");
    if(db.sql("UPDATE cpq_machine_requests SET state='DISPATCHING' WHERE request_id=:id AND state='AUTHORIZED' AND pg_try_advisory_xact_lock(hashtext(:pilot)) AND NOT EXISTS(SELECT 1 FROM cpq_machine_requests other WHERE other.pilot_id=:pilotId AND (other.state='DISPATCHING' OR (other.state='FAILED_OR_AMBIGUOUS' AND (other.slot<>'SOURCE_FIDELITY' OR :source=false))))").param("id",requestId).param("pilot",pilotId.toString()).param("pilotId",pilotId).param("source","SOURCE_FIDELITY".equals(row.get("slot"))).update()!=1)return view(pilotId,r);
    try {
      var payload=new LinkedHashMap<String,Object>();payload.put("requestId",requestId.toString());payload.put("input",row.get("input"));payload.put("authorization",row.get("authorization"));
      var response=ml.workflow("cpq-pilot/execute",payload);
      db.sql("UPDATE cpq_machine_requests SET response=CAST(:response AS jsonb) WHERE request_id=:id AND state='DISPATCHING'").param("response",encode(response)).param("id",requestId).update();
      if(!"COMPLETED".equals(response.get("executionStatus")))throw new IllegalArgumentException("Machine contract rejected; raw response retained");
      validateSingleSource(map(row.get("input")),response);
      var auth=map(row.get("authorization"));
      if(!Objects.equals(response.get("provider"),auth.get("provider"))||!Objects.equals(response.get("model"),auth.get("model"))||!(response.get("costUsd") instanceof Number cost)||!Double.isFinite(cost.doubleValue())||cost.doubleValue()<0||cost.doubleValue()>((Number)auth.get("maxCostUsd")).doubleValue())throw new IllegalArgumentException("Provider provenance/cost contract invalid");
      if(!requestId.toString().equals(response.get("requestId")))throw new IllegalArgumentException("Response request identity mismatch");
      var expectedIds=rows(map(row.get("input")).get("packets")).stream().map(x->x.get("neutralId")).collect(java.util.stream.Collectors.toSet());
      if(!rows(response.get("results")).stream().map(x->x.get("neutralId")).collect(java.util.stream.Collectors.toSet()).equals(expectedIds))throw new IllegalArgumentException("Response subjects mismatch");
      if(!"MACHINE_REVIEW".equals(response.get("evidenceType"))||rows(response.get("results")).size()!=rows(map(row.get("input")).get("packets")).size())throw new IllegalArgumentException("Complete labelled machine response required");
      var evidence=new LinkedHashMap<String,Object>();evidence.put("slot",row.get("slot"));evidence.put("requestId",requestId.toString());evidence.put("inputSha256",hash(encode(row.get("input"))));evidence.put("outputSha256",hash(encode(response)));evidence.put("rubricVersion",CreativePromptQualityService.RUBRIC);evidence.put("policyVersion",POLICY);evidence.put("response",response);evidence.put("authorization",auth);evidence.put("evidenceScope","TEXT_ONLY");
      var scope=map(pilot(pilotId,r,false).get("snapshot"));var firstSubject=rows(scope.get("subjects")).getFirst();
      evidence.put("sourceStorySha256",firstSubject.get("approvedStorySha256"));evidence.put("productionSettingsSha256",firstSubject.get("productionSettingsSha256"));evidence.put("promptBindings",rows(map(row.get("input")).get("packets")).stream().map(packet->Map.of("neutralId",packet.get("neutralId"),"promptSha256",packet.get("promptSha256"))).toList());
      persistCompleted(pilotId,requestId,encode(response),encode(evidence),String.valueOf(response.get("provider"))+":"+response.get("model"));
    }catch(Exception failure){db.sql("UPDATE cpq_machine_requests SET state='FAILED_OR_AMBIGUOUS',failure=:failure,completed_at=now() WHERE request_id=:id AND state='DISPATCHING'").param("failure","Dispatch or response contract failed; saved request must be reviewed; no automatic retry").param("id",requestId).update();}
    return view(pilotId,r);
  }
  private void persistCompleted(UUID pilot,UUID request,String response,String evidence,String actor){
    // Single database statement atomically appends evidence and completes durable request.
    db.sql("WITH completed AS (UPDATE cpq_machine_requests SET state='COMPLETED',response=CAST(:response AS jsonb),completed_at=now() WHERE request_id=:request AND state='DISPATCHING' RETURNING request_id) INSERT INTO cpq_pilot_evidence(evidence_id,pilot_id,request_id,evidence_type,actor,payload) SELECT :evidence,:pilot,request_id,'MACHINE_REVIEW',:actor,CAST(:payload AS jsonb) FROM completed").param("response",response).param("request",request).param("evidence",UUID.randomUUID()).param("pilot",pilot).param("actor",actor).param("payload",evidence).update();
  }
  @Transactional public Map<String,Object> decision(UUID id,Map<String,Object> body,HttpServletRequest r){
    pilot(id,r,true);String decision=String.valueOf(body.get("decision"));if(!Set.of("KEEP_ORIGINAL","REQUEST_REVISION","ACCEPT_TEXT_FOR_PREPARATION").contains(decision)||String.valueOf(body.getOrDefault("rationale","")).trim().length()<20||!Boolean.TRUE.equals(body.get("confirmUngradedNoRender")))throw new ResponseStatusException(BAD_REQUEST,"Explicit ungraded decision, concrete rationale and no-render confirmation required");
    if(decision.equals("ACCEPT_TEXT_FOR_PREPARATION")) {
      if(!sourceGate(id,r) || db.sql("SELECT count(*) FROM cpq_machine_requests WHERE pilot_id=:id AND slot IN ('CRITIC_A','CRITIC_B') AND state='COMPLETED'").param("id",id).query(Integer.class).single()!=2)throw new ResponseStatusException(CONFLICT,"All three independent stage results required for acceptance");
      // Owner must acknowledge conflicts/UNKNOWN explicitly; never a human PASS or render admission.
      if(rows(map(pilot(id,r,true).get("snapshot")).get("subjects")).stream().noneMatch(s->Objects.equals(s.get("promptSha256"),body.get("subjectPromptSha256"))))throw new ResponseStatusException(CONFLICT,"Exact accepted pilot subject required");
      if(!Boolean.TRUE.equals(body.get("acknowledgeMachineLimitations")))throw new ResponseStatusException(CONFLICT,"Explicit acknowledgement of machine limitations/unknowns required");
    }
    var payload=new LinkedHashMap<String,Object>(body);payload.put("policyVersion",POLICY);payload.put("evidenceType","OWNER_DECISION");payload.put("officialGrading","INACTIVE");payload.put("renderAuthorized",false);
    db.sql("INSERT INTO cpq_pilot_evidence(evidence_id,pilot_id,evidence_type,actor,payload) VALUES(:id,:pilot,'OWNER_DECISION',:owner,CAST(:payload AS jsonb))").param("id",UUID.randomUUID()).param("pilot",id).param("owner",owner(r)).param("payload",encode(payload)).update();return view(id,r);
  }
}
