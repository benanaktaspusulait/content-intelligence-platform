package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.Test;

/** OFFLINE_REVALIDATION_ONLY: pure validators; no database/client/provider can be used. */
@SuppressWarnings("unchecked")
class CpqSourceCitationTest {
  final ObjectMapper json=new ObjectMapper();
  final CpqOwnerPilotService service=new CpqOwnerPilotService(null,json,null,null);
  Map<String,Object> saved() throws Exception {
    var path=Path.of("../docs/cpq-single-subject-delivery-evidence/real-original-only-durable-result.json");
    if(!Files.exists(path))path=Path.of("intelligence/docs/cpq-single-subject-delivery-evidence/real-original-only-durable-result.json");
    return json.readValue(Files.readString(path),Map.class);
  }
  Map<String,Object> offlineEnvelope(Map<String,Object> row) throws Exception {
    var envelope=new LinkedHashMap<>((Map<String,Object>)row.get("response"));
    var raw=json.readValue((String)envelope.get("rawResponse"),Map.class);
    envelope.put("results",raw.get("results")); // Only an in-memory diagnostic view, never a completion command.
    assertThat(envelope.get("executionStatus")).isEqualTo("FAILED_OR_AMBIGUOUS");return envelope;
  }
  Map<String,Object> input(Map<String,Object> row){return (Map<String,Object>)row.get("input");}
  Map<String,Object> packet(Map<String,Object> row){return ((List<Map<String,Object>>)input(row).get("packets")).getFirst();}
  Map<String,Object> judgment(Map<String,Object> envelope){return ((List<Map<String,Object>>)envelope.get("results")).getFirst();}
  Map<String,Object> order(Map<String,Object> envelope){return ((List<Map<String,Object>>)judgment(envelope).get("mappings")).get(11);}
  String span(Map<String,Object> packet,int first,int last){String source=(String)packet.get("approvedStory");var events=(List<Map<String,Object>>)packet.get("requiredEvents");return source.substring(source.offsetByCodePoints(0,((Number)events.get(first).get("sourceStart")).intValue()),source.offsetByCodePoints(0,((Number)events.get(last).get("sourceEnd")).intValue()));}

  @Test void exactSavedRealFailAdmitsItsBoundedRangeWithoutCompletingTheRequest() throws Exception {
    var row=saved();String unchanged=json.writeValueAsString(row);var envelope=offlineEnvelope(row);
    assertThat(service.citationEventRange(packet(row),order(envelope))).containsExactly("event_06","event_07","event_08");
    service.validateSingleSource(input(row),envelope);
    assertThat(judgment(envelope).get("decision")).isEqualTo("FAIL");assertThat(row.get("state")).isEqualTo("FAILED_OR_AMBIGUOUS");assertThat(json.writeValueAsString(row)).isEqualTo(unchanged);
  }
  @Test void everyActualQuotePassesAndSingleEventCoverageIsStillRequired() throws Exception {
    var row=saved();var envelope=offlineEnvelope(row);var mappings=(List<Map<String,Object>>)judgment(envelope).get("mappings");
    for(int i=0;i<mappings.size();i++)assertThat(service.citationEventRange(packet(row),mappings.get(i))).hasSize(i==11?3:1);
    mappings.removeIf(m->"APPROVED_EVENTS".equals(m.get("anchor"))&&"event_07".equals(m.get("eventId")));
    assertThatThrownBy(()->service.validateSingleSource(input(row),envelope)).hasMessageContaining("Complete source evidence");
  }
  @Test void twoEventRangeWorksWithEitherIncludedAnchor() throws Exception {
    var row=saved();var envelope=offlineEnvelope(row);var mapping=order(envelope);mapping.put("sourceQuote",span(packet(row),5,6));
    for(String anchor:List.of("event_06","event_07")){mapping.put("eventId",anchor);assertThat(service.citationEventRange(packet(row),mapping)).containsExactly("event_06","event_07");}
  }
  @Test void invalidRangesDoNotRelaxOtherSourceEvidence() throws Exception {
    for(String defect:List.of("noncontiguous","reordered","fabricated","wrong_anchor","wrong_kind","whole_story","four_events","partial_boundary","unknown_event","whitespace")){
      var row=saved();var envelope=offlineEnvelope(row);var mapping=order(envelope);var p=packet(row);
      switch(defect){
        case "noncontiguous"->mapping.put("sourceQuote",span(p,5,5)+" "+span(p,7,7));
        case "reordered"->mapping.put("sourceQuote",span(p,7,7)+" "+span(p,6,6)+" "+span(p,5,5));
        case "fabricated"->mapping.put("sourceQuote",mapping.get("sourceQuote")+" Invented story event.");
        case "wrong_anchor"->mapping.put("eventId","event_05");
        case "wrong_kind"->mapping.put("anchor","APPROVED_EVENTS");
        case "whole_story"->mapping.put("sourceQuote",p.get("approvedStory"));
        case "four_events"->mapping.put("sourceQuote",span(p,4,7));
        case "partial_boundary"->mapping.put("sourceQuote",((String)mapping.get("sourceQuote")).substring(1));
        case "unknown_event"->mapping.put("eventId","event_99");
        case "whitespace"->mapping.put("sourceQuote",((String)mapping.get("sourceQuote")).replaceFirst("\\. ",".  "));
      }
      assertThatThrownBy(()->service.validateSingleSource(input(row),envelope)).as(defect).isInstanceOf(IllegalArgumentException.class);
    }
  }
  @Test void completeUnknownAndFailRemainAdmissibleButUnsupportedPassDoesNot() throws Exception {
    for(String decision:List.of("FAIL","UNKNOWN")){var row=saved();var envelope=offlineEnvelope(row);judgment(envelope).put("decision",decision);service.validateSingleSource(input(row),envelope);}
    var row=saved();var envelope=offlineEnvelope(row);judgment(envelope).put("decision","PASS");assertThatThrownBy(()->service.validateSingleSource(input(row),envelope)).hasMessageContaining("Unsupported semantic PASS");
  }
  @Test void missingAnchorIsStillRejected() throws Exception {
    var row=saved();var envelope=offlineEnvelope(row);((List<Map<String,Object>>)judgment(envelope).get("mappings")).removeIf(m->"PHYSICAL_RULE".equals(m.get("anchor")));assertThatThrownBy(()->service.validateSingleSource(input(row),envelope)).hasMessageContaining("Complete source evidence");
  }
}
