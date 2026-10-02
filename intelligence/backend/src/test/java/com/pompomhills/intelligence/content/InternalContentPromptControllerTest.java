package com.pompomhills.intelligence.content;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class InternalContentPromptControllerTest {
  private ContentPromptQueryService service;
  private MockMvc mvc;

  @BeforeEach
  void setUp() {
    service = org.mockito.Mockito.mock(ContentPromptQueryService.class);
    mvc = MockMvcBuilders.standaloneSetup(new InternalContentPromptController(service)).build();
  }

  @Test
  void returnsVersionedSnapshotContract() throws Exception {
    when(service.load(10L, 11L))
        .thenReturn(
            new ContentPromptSnapshot(
                "v1",
                10L,
                "Kiko Discovers Rain",
                "EPISODE",
                "RENDER_READY",
                11L,
                3,
                "gentle rain",
                "{\"scene\":1}",
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"));

    mvc.perform(get("/api/v1/intelligence/contents/10/prompt-versions/11"))
        .andExpect(status().isOk())
        .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
        .andExpect(jsonPath("$.contractVersion").value("v1"))
        .andExpect(jsonPath("$.contentId").value(10))
        .andExpect(jsonPath("$.promptVersionId").value(11))
        .andExpect(jsonPath("$.promptText").value("gentle rain"))
        .andExpect(
            jsonPath("$.promptSha256")
                .value("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"));
  }

  @Test
  void mapsMissingOwnershipToStableProblemDetailWithoutPromptText() throws Exception {
    when(service.load(10L, 99L)).thenThrow(new ContentPromptNotFoundException(10L, 99L));

    mvc.perform(get("/api/v1/intelligence/contents/10/prompt-versions/99"))
        .andExpect(status().isNotFound())
        .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
        .andExpect(jsonPath("$.title").value("Content prompt snapshot not found"))
        .andExpect(jsonPath("$.detail").value("No prompt version 99 belongs to content 10"))
        .andExpect(jsonPath("$.status").value(404))
        .andExpect(
            content()
                .string(
                    org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("promptText"))));
  }
}
