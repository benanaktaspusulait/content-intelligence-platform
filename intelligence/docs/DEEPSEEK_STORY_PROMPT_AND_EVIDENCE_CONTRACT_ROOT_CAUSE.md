ACTUAL_DEEPSEEK_STORY_CALLS_ANALYZED: 2
AUTHENTIC_STORIES_ANALYZED: 4

NEW_PROVIDER_CALLS: 0
NEW_PROVIDER_SPEND_USD: 0

EXACT_OUTBOUND_PROMPTS_RECOVERED: YES
CONTRADICTORY_INSTRUCTIONS_FOUND: 0_PROVEN_UNSATISFIABLE; 4_COMPETING_REQUIREMENT_GROUPS; LAYERED_SCHEMA_AMBIGUITY

MODEL_AUTHORED_QUOTE_ERRORS_FOUND: 6
ACTUAL_SOURCE_VIOLATIONS_FOUND: 1_UNAPPROVED_RETREAT_TRIGGER_IN_CALL_1_CANDIDATE_1; OTHER_SEMANTICS_UNVERIFIED
DETERMINISTIC_FALSE_REJECTIONS_FOUND: 0_UNDER_LITERAL_POLICY; 2_EVIDENCE_ERRORS_LABELLED_SOURCE_VIOLATION
SEMANTICALLY_UNRESOLVED_CASES: 4

CREATIVE_FREEDOM_CONSTRAINTS_AUDITED: YES
PROTECTED_VS_REVISABLE_MATRIX_COMPLETE: YES

EVIDENCE_EXTRACTION_CONTRACT: VERIFIED
FOUR_RESPONSE_OFFLINE_REPLAY: PASS

CURRENT_PAID_REVIEW_GATES_WEAKENED: NO
OWNER_APPROVAL_REQUIREMENTS_PRESERVED: YES

PRODUCTION_DB_WRITES: 0
GIT_HISTORY_MODIFICATIONS_BY_AGENT: 0

TEST_RESULTS: 213_ML_PASSED; 40_BACKEND_PASSED; EXIT_CODES_0
NEXT_PAID_EXPERIMENT_AUTHORIZED: NO

RECOMMENDED_ACTION: REUSE_EXISTING_STORIES_FOR_SEPARATELY_AUTHORIZED_INDEPENDENT_REVIEW

# Conclusion

The observed stopping pattern is primarily an **authoring/evidence responsibility problem**, with real model citation mistakes and at least one substantive story-trigger defect. It is not evidence that DeepSeek cannot create better stories. Only two related generation requests exist, both highly anchored to the same source; no independent reviewer has evaluated any output. Nor is there evidence yet that these four stories are materially better.

The strict gate did what the owner-approved literal contract required. The design mistake is making source-meaning assessment depend on the creative generator reproducing and certifying its own exact phrases, then using one SOURCE_VIOLATION label for both absent quotations and narrative contradiction. The second response demonstrates this directly: four protected clauses and all required narrative excerpt fields were correct; a single absent continuity citation in each otherwise complete narrative stopped the entire pair.

The smallest implemented correction is an **offline, unactivated separation** using the existing story-evidence module: preserve the authored narrative, derive exact locations mechanically, invalidate false evidence claims separately, and leave source semantics UNKNOWN. Current strict paid admission remains unchanged. A proposal to allow UNKNOWN source meaning into a separately authorized independent semantic assessment requires an explicit owner policy decision; this task does not grant it or spend the unused budgets.

# A. Exact request audit

## Recovery and provenance

Both saved outbound request artifacts include complete system and user message strings; they were compared with saved receipt bindings and source fingerprints. All 16 original first-run evidence hashes and all 17 follow-up evidence hashes still match. The complete byte-preserved prompt strings and copies of the saved request artifacts are provided below. No hypothetical prompt replaced the real requests.

These are application/preflight-backed outbound artifacts, not an independent network packet capture. The provider response supplies model, ID, finish reason and usage, but does not echo the complete incoming messages. Uncaptured provider defaults or private model processing are unavailable. The recorded effective request SHA binds the user JSON; the separately recorded system SHA binds its instructions. They must not be conflated with a hash of the whole SDK HTTP envelope.

| Field | First real call | Follow-up call |
|---|---|---|
| Provider / endpoint | DeepSeek / api.deepseek.com chat completions | Same |
| Requested model | deepseek-chat | deepseek-flash |
| Returned model | deepseek-flash; exact identity gate rejected | deepseek-flash; exact identity matched |
| Explicit thinking field | Absent in saved request; effective provider default unavailable | disabled |
| Temperature | 0 | 0 |
| Candidate count | 2 requested; 2 returned | 2 requested; 2 returned |
| Output cap / used | 4,000 / 1,453 | 4,000 / 1,422 |
| Finish reason | stop | stop |
| Input tokens | 3,651 | 3,926 |
| response_format | json_object | json_object |
| Enforced provider JSON schema | NONE captured/sent | NONE captured/sent |
| Whole-source copies in user JSON | text + context.approvedStoryText | Same two copies |
| Full creative-validity assessment object | Not supplied | Not supplied |
| Full original/canonical reference catalog | Five protected spans plus saved IDs and compact canonical findings | Same |
| Examples | A three-field one-candidate JSON shape, not a complete worked narrative | Same shape plus longer evidence instructions |

The response format guarantees JSON syntax, not the prose-described candidate schema. The field `schemaVersion=story-pilot-candidates-v1` is an application output requirement, not an SDK-enforced JSON Schema. The original artifact's `automaticRetries`, the second artifact's `max_retries`, and `effectivePayloadSha256` describe client policy/SDK settings/local bindings; they are not model-authored output or additional message text. Actual adapters use max_retries=0. No complete few-shot improved narrative or independent reviewer example was sent.

**call-1:** full [system prompt](deepseek-story-root-cause-evidence/call-1-exact-system.txt), full [user prompt](deepseek-story-root-cause-evidence/call-1-exact-user.txt), [saved outbound artifact](deepseek-story-root-cause-evidence/call-1-saved-request.json). System/user sizes: **4301 / 10221 bytes**. System SHA `f7e53b14f26b2608e6b075fec79ca63408df83aa759c001081a898e82cbf3d4a`; user SHA `9911fb57fc276c6631bcb1aea4378024a55cf00388509fd63b0dc83cb77813e1`. Raw response SHA `34bc110e50779d47964b3546cd3e5f69b9ac8ea773f9a63aee1e04f2281359d1`.

**call-2:** full [system prompt](deepseek-story-root-cause-evidence/call-2-exact-system.txt), full [user prompt](deepseek-story-root-cause-evidence/call-2-exact-user.txt), [saved outbound artifact](deepseek-story-root-cause-evidence/call-2-saved-request.json). System/user sizes: **5880 / 10221 bytes**. System SHA `84f6882229fd8ee8c96d064e32588794105fef0af365e7d648eac28d97a9e30d`; user SHA `9911fb57fc276c6631bcb1aea4378024a55cf00388509fd63b0dc83cb77813e1`. Raw response SHA `10dc1482d66514e153835b6e3cd90f4e8b58ff1e1d61f51fa99e42424f15fef3`.

The user-message bytes are identical across calls; only the system instructions, model identity and explicit non-thinking setting changed. The first full system has 4,301 UTF-8 bytes; the second adds 1,579 bytes of evidence guidance. Neither response exhausted its output limit. A larger token budget is not justified by these receipts.

## What was in the user context

The complete source story was supplied twice, plus five protected quotes with Unicode offsets. Source ID `ca40c11a-7831-476e-9f50-646a61a1ec9c`, approval `af738239-99c3-4a9e-90b5-a1bee4295cd0`, revision `candidate-1-revision-04c8c36b`, analysis `10fc4c38-7cdf-4f71-b8dc-05b14315352a`. Source SHA `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d`. The objective identifies 15s, ABSURD_PHYSICS, SEEDANCE_2_0_MINI, image2video, 480p, 9:16, and asks for natural pacing, distinct visible consequences, less ending overload and honest thin-object risk.

The compact canonical context has 13 findings: PRODUCIBILITY_003, INSTANT_VISUAL_ABSURDITY_GATE and ENGINE_SILHOUETTE_DUPLICATE are FAIL; CONSISTENCY_001, HOOK_003, ATTEMPT_002, PAYOFF_003, CONCEPT_007, GOAL_001, CONCEPT_008, HOOK_004, PERFORMANCE_001 and GENERATION_EXECUTABLE_ATTEMPTS are UNKNOWN. Their full saved messages are in each exact user JSON. The context also supplies baseline 93.42708333333334/A, target CANONICAL_A/92, current/optimistic ceiling, three source attempts, and an old **prompt-only** generationAllowed=false eligibility result. That result is not a prohibition on the separately authorized Story Evolution role, but its mixed scope is unnecessary cognitive load in a creative-authoring request.

The full creative-validity assessment was **not** sent. Creative weaknesses were represented by the objective, nine creativeRequirements, canonical finding messages, prohibitedShortcuts and a prompt-only preflight explanation. No image, first frame, audience metrics, independent source judgment, reference silhouette catalog or verified Seedance result was supplied. A canonical score from a deterministic baseline is not real creative quality evidence.

## Instruction locations and interaction

Locations below refer to exact strings under `messages[0].content` or JSON pointers in the saved user JSON. Machine-readable substring offsets are in [request-audit.json](deepseek-story-root-cause-evidence/request-audit.json).

| Requirement | Actual location / wording | Interaction |
|---|---|---|
| Different narratives | System: “Vary at least one of: action/progression strategy…” | Genuine creative variation requested, but most source machinery remains anchored |
| Preserve exact entire original story | **Not instructed** | Do not import the unrelated PROMPT_OPTIMIZATION instruction to freeze all events into this STORY audit |
| Preserve only locks | System generic STORY block; /context/lockedRequirements | KEY_EVENTS is not in the actual list; identity/premise/rule/ending are |
| Keep protected facts | System strict block: “Every protectedAnchors quote must remain an affirmative unchanged fact…” | Call 1 leaves fact-versus-verbatim interpretation partly implicit |
| Copy protected clauses verbatim | Call 2 Evidence contract v2 block | Explicit literal condition over and above semantic preservation |
| Paraphrase protected facts | **Not instructed** | The model paraphrased or omitted literal clauses despite the requirement |
| Quote own narrative | System: four excerpt fields, then call 2 exact contiguous-substring guidance | Same generator must write and accurately cite its own prose |
| Quote original source | sourceContract sourceQuote plus /context/storyExperiment/protectedAnchors | Repeats original catalog and invites copy-from-source errors in candidateQuote |
| Scoring | System says not a manufactured numeric score; context target=92/baseline=A + rule lists | No instruction explicitly says maximize score, but a strong implicit rule-coverage target remains |
| Protected changes | System requires anchorId/proposedChange/justification and proposal status | Legitimate proposal channel exists, but current pilot rejects such a proposal before review |
| Distinct consequences / less complexity | System final creative block + /context/objective | Difficult to remove fragile note/face/sneeze elements while several are protected |
| Initial JSON “schema” | System begins with candidateId/title/text example; later strict block adds many fields | Compatible as an extension but ambiguous as a claimed exact schema; no formal schema resolves it |

There is no demonstrated unsatisfiable logical instruction pair. There are four materially competing groups: creative novelty versus narrow locks; authoring versus self-certification; anti-score language versus numeric/rule-heavy context; thin-object simplification versus a thin-object premise and covered-body/sneeze ending. Count-range 1–3 versus exact 2 is a specialization, not a logical contradiction. Generic statement that “only listed requirements are binding” is clarified later by the explicit protected anchor contract; leaving it layered still obscures the source of authority.

# B. Creative freedom and source locks

| Element | Category / authoritative location | Current protection | Revision freedom |
|---|---|---|---|
| Pip the rabbit | Character identity; identity anchor | Exact identity clause locked | No automatic identity replacement; appearance/reference details are not supplied |
| Child-appropriate channel tone | Channel intent; requested future mode principle | No dedicated tone/style field found in these actual requests | Must be explicitly specified in a future scope; do not invent an unseen channel bible |
| Sticky note / cabinet / fingertip / untouched cabinet | Concept identity; premise anchor | Locked | Staging may vary while preserving the relationship |
| Removal or transfer attempts multiply notes | Single-mechanic invariant; rule anchor | Locked | New independent trigger is not a harmless action rename |
| Exactly two, four, eight | Historically approved progression, not literal anchor numerals | Not separately locked in the five anchors | Could be proposed differently if faithful to the original physical rule; no silent change to approved source |
| Three named attempts | Historical events + canonical context pressure | No PRESERVE_KEY_EVENTS lock supplied | Actions/order can be proposed differently; adding attempts purely to score is prohibited |
| Arm/face coverage specifics | Historical visual development | Core covered state protected; exact placement less specified | Presentation choices possible; character/reference continuity remains unknown |
| Realization and deliberate stop | Historical events, promoted by creative/rule instructions | Not a separate protected anchor | May be redesigned as an observable agency/reversal proposal |
| Mirror turn/reaction | Historical presentation | **Not protected** by the actual anchor list | Omission is not a protected-fact violation by itself |
| Remain covered until sneeze; scatter onto cabinet | Pilot-specific continuity lock | Protected clause | No release before sneeze or replacement release without proposal/owner decision |
| Relief with messy cabinet | Required ending; ending anchor | Protected clause | No different ending in source-bound mode without explicit proposal |
| 15s / generator / mode / resolution / ratio | Production settings | Same exact saved setting scope | Story author may propose pacing, not certify execution or silently change settings |

The locks leave room for staging, action choice, timing and realization, but preserve the premise, multiplying-paper engine and final release/state. They make a radically different visual engine or ending unavailable in the current source-bound pilot. Nothing forces every original sentence to be copied. Nothing in the evidence proves that meaningful improvement inside these limits is impossible; four related outputs only show limited exploration under this particular prompt and model setting.

Two future modes can reuse Story Evolution: SOURCE-BOUND STORY REVISION keeps those facts and marks uncertainty; CREATIVE EXPLORATION PROPOSAL may propose exact protected changes while preserving explicitly approved channel identity, age-appropriate tone and coherent causality. Neither changes the approved source or admits production. This task activates neither mode nor a new spending policy.

# C. Four authentic stories and three separate judgments

Every narrative below is verbatim from its own immutable raw response. Provisional assessments are this offline code/evidence audit, **not** an independent AI or human-review record. No official grade, score, retention forecast or winner is assigned.

## call-1/candidate-1: The One-Note Problem

Immutable response SHA: `34bc110e50779d47964b3546cd3e5f69b9ac8ea773f9a63aee1e04f2281359d1`; candidate SHA: `7ec0ee071b06e13b4171c4cb68d4058b3d6de8109d32c5cc3e6a339b86a0983b`.

Pip the rabbit stands before the toy cabinet's bare front panel, one sticky note pinched between two fingers, already reaching to press it flat. The note clings to Pip's fingertip while the cabinet stays untouched. Pip peels it with the free hand and it splits into two notes, one stuck to each hand. Pip presses both palms to the cabinet; they spring back and double into four notes, now dotting Pip's wrists. Pip backs away, arms out, and the four notes split into eight across Pip's arms and face. Pip freezes, eyes wide above a note stuck to the muzzle, and watches the last split finish. Pip deliberately lowers both arms and stops struggling. The still note-covered face turns toward the mirror. Pip holds still, breathing, until a sneeze bursts out and scatters the notes onto the cabinet. Pip is relieved, but the cabinet remains messy.

**Structural contract:** original strict source result `UNKNOWN`, paid review blocked. **Narrative structure under proposed extraction:** `COMPLETE_BOUNDED_NARRATIVE`. **Independent creative verification:** NOT_EXECUTED.

**Actual source mappings authored by the model:**

| Anchor | sourceQuote | candidateQuote | Literal citation / invariant issue |
|---|---|---|---|
| identity | Pip the rabbit | Pip the rabbit | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| premise | it clings to Pip's fingertip while the cabinet stays untouched | The note clings to Pip's fingertip while the cabinet stays untouched. | EXACT_QUOTE_PRESENT; MISSING |
| rule | every removal or transfer attempt multiplies the notes | Pip peels it with the free hand and it splits into two notes | EXACT_QUOTE_PRESENT; MISSING |
| continuity | Pip remains covered until a sneeze scatters the notes onto the cabinet | Pip holds still, breathing, until a sneeze bursts out and scatters the notes onto the cabinet. | EXACT_QUOTE_PRESENT; MISSING |
| ending | Pip is relieved, but the cabinet remains messy. | Pip is relieved, but the cabinet remains messy. | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |

A valid literal candidateQuote is not necessarily a complete source-invariant mapping. Missing exact protected text remains MISSING/semantic UNKNOWN even when a different cited sentence exists.

**Invalid model evidence claims:**

- motivation: `Pip wants to place a single sticky note flat on the cabinet's empty front panel.` is not an accurate complete cited excerpt/claim.
- progression: `The note clings to Pip's fingertip while the cabinet stays untouched; peeling splits it into two, pressing doubles them to four, and backing away splits them to eight across Pip's arms and face.` is not an accurate complete cited excerpt/claim.

**Provisional assessment using the six existing CPQ dimensions:**

| Dimension | Text-based observation and uncertainty |
|---|---|
| SCROLL_STOP_VISUAL_PROMISE | Opens with reaching toward an ordinary bare panel, then attachment. Text may delay the abnormal promise relative to the already-mid-action baseline; no first frame exists. |
| CAUSAL_PROGRESSION | Peel and press are removal/transfer-directed. Backing away alone makes four split to eight; proposedChanges explicitly calls retreat the trigger. That is an unapproved trigger deviation under the intended single mechanic. |
| VISUAL_STORYTELLING | Wrist/body silhouette and lowering arms are readable intentions; still mostly note count and coverage. Extra verbs do not establish a new consequence engine. |
| PRODUCTION_EXECUTABILITY | Pinching thin paper, wrist coverage, muzzle note, mirror turn and scatter retain precision/occlusion risk. No timing plan verifies the held breathing plus mirror/sneeze load. |
| ENDING_REPLAY | Relief/messy cabinet remains; mirror and held breath may crowd the ending. Replay value is UNKNOWN. |
| DISTINCTIVE_CREATIVE_VALUE | Retreat silhouette is an observable proposal but causally problematic. No defensible superiority established. |

**Model-declared changes, preserved as self-report:**

- Open on the single-note placement attempt rather than mid-multiplication so the first visible promise is the rule itself.
- Replace the door-edge push with a backward retreat that triggers the four-to-eight split, giving a clearer full-body silhouette.
- Move the realization to a deliberate lowering of arms and a held still beat before the mirror turn, so the reversal is earned rather than rushed.

**Model-declared risks, not independent evidence:**

- THIN_OBJECT precision on note-to-fingertip and note-to-face contact.
- Face partially occluded by a note during the realization beat.
- Sneeze scatter requires many small notes to move believably in one burst.

## call-1/candidate-2: Stop Trying

Immutable response SHA: `34bc110e50779d47964b3546cd3e5f69b9ac8ea773f9a63aee1e04f2281359d1`; candidate SHA: `50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088`.

Pip the rabbit presses a single sticky note toward the toy cabinet's empty front panel, and it clings to Pip's fingertip while the cabinet stays untouched. Pip shakes the hand; the note splits into two, one on each hand. Pip claps both hands onto the cabinet to transfer them, but they bounce back and double into four notes stuck across Pip's chest. Pip grabs at the four with both arms and they split into eight, wrapping Pip's arms and face. Pip sees the doubling finish and goes still, then slowly sits down on the floor, arms folded, refusing to touch anything. The notes stay put. Pip's nose twitches; a sneeze erupts and scatters the notes onto the cabinet. Pip is relieved, but the cabinet remains messy.

**Structural contract:** original strict source result `UNKNOWN`, paid review blocked. **Narrative structure under proposed extraction:** `COMPLETE_BOUNDED_NARRATIVE`. **Independent creative verification:** NOT_EXECUTED.

**Actual source mappings authored by the model:**

| Anchor | sourceQuote | candidateQuote | Literal citation / invariant issue |
|---|---|---|---|
| identity | Pip the rabbit | Pip the rabbit | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| premise | it clings to Pip's fingertip while the cabinet stays untouched | it clings to Pip's fingertip while the cabinet stays untouched | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| rule | every removal or transfer attempt multiplies the notes | Pip grabs at the four with both arms and they split into eight | EXACT_QUOTE_PRESENT; MISSING |
| continuity | Pip remains covered until a sneeze scatters the notes onto the cabinet | a sneeze erupts and scatters the notes onto the cabinet | EXACT_QUOTE_PRESENT; MISSING |
| ending | Pip is relieved, but the cabinet remains messy. | Pip is relieved, but the cabinet remains messy. | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |

A valid literal candidateQuote is not necessarily a complete source-invariant mapping. Missing exact protected text remains MISSING/semantic UNKNOWN even when a different cited sentence exists.

**Invalid model evidence claims:**

- motivation: `Pip wants to transfer the sticky note onto the cabinet and be done with it.` is not an accurate complete cited excerpt/claim.
- progression: `Shaking splits the note into two, clapping doubles them to four across Pip's chest, and grabbing splits them to eight over arms and face; Pip then sits down and refuses to touch anything.` is not an accurate complete cited excerpt/claim.

**Provisional assessment using the six existing CPQ dimensions:**

| Dimension | Text-based observation and uncertainty |
|---|---|
| SCROLL_STOP_VISUAL_PROMISE | Starts on pressing/attachment conflict; potentially immediate problem legibility, not verified scroll stop. |
| CAUSAL_PROGRESSION | Shake/clap-transfer/grab then refusal. Clap explicitly transfers; shake/grab removal intent and continuity require semantic assessment. |
| VISUAL_STORYTELLING | Sit-down with folded arms is a genuinely different visible decision from a mirror look and could communicate refusing the trap. Whether viewers read realization or giving up is unknown. |
| PRODUCTION_EXECUTABILITY | Chest/arm/face notes, sit-down, nose twitch and scatter remain difficult and temporally dense at 480p. Removing the mirror does not prove a simpler total sequence. |
| ENDING_REPLAY | Sneeze releases after stillness, same relief/messy outcome. No new loop/replay evidence. |
| DISTINCTIVE_CREATIVE_VALUE | The surrender gesture has a specific narrative hypothesis worth independent criticism; no independent creative win is established. |

**Model-declared changes, preserved as self-report:**

- Replace the mirror turn with a deliberate sit-down refusal, making the realization a full-body surrender rather than a look.
- Use a clap-to-transfer attempt instead of a press, giving a distinct two-hand silhouette at the four-note stage.
- Keep the sneeze as the only release, so the payoff is earned by Pip's stillness rather than a mirror beat.

**Model-declared risks, not independent evidence:**

- THIN_OBJECT precision on note-to-chest and note-to-face contact.
- Sit-down motion plus note scatter in the final seconds risks crowding.
- Sneeze burst with many small notes may not read cleanly at 480p.

## call-2/candidate-1: The Sticky Note That Won't Leave Pip

Immutable response SHA: `10dc1482d66514e153835b6e3cd90f4e8b58ff1e1d61f51fa99e42424f15fef3`; candidate SHA: `4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739`.

Pip the rabbit reaches to smooth one sticky note onto the toy cabinet's bare front panel, but it clings to Pip's fingertip while the cabinet stays untouched. Pip pinches the note with the other paw to peel it free, and it splits into two notes, one stuck to each paw. Pip slaps both paws toward the cabinet, but the notes bounce back and double into four, fluttering up Pip's arms. Pip shakes both arms hard to fling the four notes away, and they split into eight, plastering Pip's chest and cheeks. Pip freezes, watching the eight notes ripple and settle, and realizes that every removal or transfer attempt multiplies the notes. Pip deliberately stops struggling and stands still, letting the notes rest. A sneeze bursts out of Pip, and the blast peels the notes off and scatters them across the cabinet. Pip is relieved, but the cabinet remains messy.

**Structural contract:** original strict source result `SOURCE_VIOLATION`, paid review blocked. **Narrative structure under proposed extraction:** `COMPLETE_BOUNDED_NARRATIVE`. **Independent creative verification:** NOT_EXECUTED.

**Actual source mappings authored by the model:**

| Anchor | sourceQuote | candidateQuote | Literal citation / invariant issue |
|---|---|---|---|
| identity | Pip the rabbit | Pip the rabbit | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| premise | it clings to Pip's fingertip while the cabinet stays untouched | it clings to Pip's fingertip while the cabinet stays untouched | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| rule | every removal or transfer attempt multiplies the notes | every removal or transfer attempt multiplies the notes | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| continuity | Pip remains covered until a sneeze scatters the notes onto the cabinet | Pip remains covered until a sneeze scatters the notes onto the cabinet | INVALID_EVIDENCE_CLAIM; MISSING |
| ending | Pip is relieved, but the cabinet remains messy. | Pip is relieved, but the cabinet remains messy. | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |

A valid literal candidateQuote is not necessarily a complete source-invariant mapping. Missing exact protected text remains MISSING/semantic UNKNOWN even when a different cited sentence exists.

**Invalid model evidence claims:**

- sourceContract.bindings / continuity: `Pip remains covered until a sneeze scatters the notes onto the cabinet` is not an accurate complete cited excerpt/claim.

**Provisional assessment using the six existing CPQ dimensions:**

| Dimension | Text-based observation and uncertainty |
|---|---|
| SCROLL_STOP_VISUAL_PROMISE | Reaches to smooth a note, then fingertip adhesion; similar immediate problem, possibly setup before anomaly. First-visible-state quality remains text-only. |
| CAUSAL_PROGRESSION | Pinch-to-peel, slap-to-transfer and shake-to-fling make attempts removal-directed, unlike the earlier retreat-only trigger. Whole-story fidelity still UNKNOWN. |
| VISUAL_STORYTELLING | Freeze and observation followed by stopping gives a visible realization intent; count escalation and coverage remain the same engine. |
| PRODUCTION_EXECUTABILITY | Removing mirror/sit-down may reduce secondary actions, but face contact, fluttering notes, held pose and sneeze scatter remain unverified. No timed IR or render exists. |
| ENDING_REPLAY | Sneeze release and relieved/messy ending retained in meaning as written; exact continuity citation absent. Payoff originality and replay UNKNOWN. |
| DISTINCTIVE_CREATIVE_VALUE | A cleaner removal-directed sequence and reduced secondary ending business are plausible improvements to assess, not confirmed gains. |

**Model-declared changes, preserved as self-report:**

- Replaces the door-edge push with an arm-shake fling so the escalation reads as one clear physical action per beat.
- Moves the realization to a held freeze before the sneeze, giving the reversal its own beat instead of crowding the final seconds.
- Removes the mirror turn to keep the payoff on Pip and the cabinet rather than a reflection.

**Model-declared risks, not independent evidence:**

- THIN_OBJECT: sticky notes contacting paws and face require precise thin-object handling.
- FACE_CONTACT: notes plastering Pip's cheeks risk face/hair continuity issues.
- SNEEZE_BURST: the scatter needs a clear directional force to read as one motion.

## call-2/candidate-2: Pip Stops Fighting the Notes

Immutable response SHA: `10dc1482d66514e153835b6e3cd90f4e8b58ff1e1d61f51fa99e42424f15fef3`; candidate SHA: `7bd179926c406f1aa2566b1f513daef9cec355ffebc15517f49168d2d92fa41b`.

Pip the rabbit presses one sticky note toward the toy cabinet's empty front panel, but it clings to Pip's fingertip while the cabinet stays untouched. Pip tries to flick the note off with a quick wrist snap, and it splits into two notes, one on each paw. Pip claps both paws together to crush the notes flat, but they spring apart into four and climb Pip's sleeves. Pip backs away and brushes the four notes off against the cabinet's side, and they split into eight, wrapping Pip's shoulders and muzzle. Pip stares at the doubling notes, breathing hard, and realizes that every removal or transfer attempt multiplies the notes. Pip slowly lowers both arms and stops moving entirely, letting the notes cling. A sneeze jerks through Pip, and the notes blow off in a burst and land across the cabinet. Pip is relieved, but the cabinet remains messy.

**Structural contract:** original strict source result `SOURCE_VIOLATION`, paid review blocked. **Narrative structure under proposed extraction:** `COMPLETE_BOUNDED_NARRATIVE`. **Independent creative verification:** NOT_EXECUTED.

**Actual source mappings authored by the model:**

| Anchor | sourceQuote | candidateQuote | Literal citation / invariant issue |
|---|---|---|---|
| identity | Pip the rabbit | Pip the rabbit | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| premise | it clings to Pip's fingertip while the cabinet stays untouched | it clings to Pip's fingertip while the cabinet stays untouched | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| rule | every removal or transfer attempt multiplies the notes | every removal or transfer attempt multiplies the notes | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |
| continuity | Pip remains covered until a sneeze scatters the notes onto the cabinet | Pip remains covered until a sneeze scatters the notes onto the cabinet | INVALID_EVIDENCE_CLAIM; MISSING |
| ending | Pip is relieved, but the cabinet remains messy. | Pip is relieved, but the cabinet remains messy. | EXACT_QUOTE_PRESENT; EXACT_TEXT_LOCATED |

A valid literal candidateQuote is not necessarily a complete source-invariant mapping. Missing exact protected text remains MISSING/semantic UNKNOWN even when a different cited sentence exists.

**Invalid model evidence claims:**

- sourceContract.bindings / continuity: `Pip remains covered until a sneeze scatters the notes onto the cabinet` is not an accurate complete cited excerpt/claim.

**Provisional assessment using the six existing CPQ dimensions:**

| Dimension | Text-based observation and uncertainty |
|---|---|
| SCROLL_STOP_VISUAL_PROMISE | Press/adhesion opening nearly repeats the source; no independently demonstrated stronger frame zero. |
| CAUSAL_PROGRESSION | Wrist flick and brush-off are removal-directed. Clap “to crush the notes flat” is not explicitly a removal/transfer attempt and may add a trigger. Needs semantic review. |
| VISUAL_STORYTELLING | Flick/clap/brush have different motion silhouettes, but consequences remain two/four/eight and body coverage. Lowering arms repeats the stop/reversal. |
| PRODUCTION_EXECUTABILITY | Fast clap at 480p, step-plus-brush, sleeves/wardrobe introduced without reference evidence, muzzle coverage and scatter add risks. |
| ENDING_REPLAY | Breath/lowered arms/sneeze same endpoint; no proof of a more satisfying or replayable ending. |
| DISTINCTIVE_CREATIVE_VALUE | Action variety is observable; stronger narrative or novelty is not established by those substitutions. |

**Model-declared changes, preserved as self-report:**

- Uses a wrist-flick and a paw-clap as the first two escalation actions, giving each beat a distinct silhouette.
- Adds a backward step before the brush-off so Pip's retreat visibly fails and motivates the freeze.
- Holds the realization on a breath and lowered arms before the sneeze, separating reversal from payoff.

**Model-declared risks, not independent evidence:**

- THIN_OBJECT: notes on paws, sleeves and muzzle need careful thin-object contact.
- FACE_CONTACT: notes wrapping the muzzle risk face continuity problems.
- MULTI_OBJECT_STACKING: eight notes spreading across shoulders and cabinet may be hard to track.

# D. Evidence fidelity is not story fidelity

Six actual invalid excerpt claims were found: motivation and progression summaries absent from both first-call narratives (four claims), then the copied source continuity sentence absent from both follow-up narratives (two claims). First-call paraphrases of premise/rule/continuity are a different issue: many candidateQuote fragments **do** occur in the story, but they do not literally state the complete protected clause. Exact quote validity and protected meaning must not be merged.

The follow-up stories describe notes remaining attached before a sneeze. That is a plausible continuity reading, not deterministic proof. An extractor must return the actual sentences and mark the protected exact clause MISSING; it must never fabricate or insert the quoted clause. An independent reviewer must assess whether those sentences preserve uninterrupted covered state. A false metadata quote stays invalid even if the narrative later receives a positive semantic assessment.

Call-1/candidate-1's retreat-triggered split is separate from its metadata mistakes. The model explicitly proposed replacing a removal attempt with retreat as trigger. Under the intended sole removal/transfer rule, that is an unapproved causal change; it must not be rehabilitated by copying a rule clause into the narrative. This is a forensic audit finding, not an executed independent review. The small deterministic extractor deliberately does not pretend to detect arbitrary trigger semantics: its generic result for this case remains review-required, and the manual risk/violation annotation stays visible and excludes an unconditional reuse recommendation for this candidate.

No literal quote false rejection was demonstrated under the **existing** authorized exact-clause policy. The system-design false inference would be treating the two latest SOURCE_VIOLATION labels as proof of invalid story meaning. The new offline report corrects that conflation without changing historical labels or paid eligibility.

# E. Minimal implemented correction and unactivated generation proposal

`story_evidence.derive_source_evidence` is a pure, provider-free function in the existing evidence component. It derives exact source/catalog spans and actual candidate occurrences, narrative sentence locations and candidate SHA. It validates model-supplied quote claims separately. Missing material stays MISSING/UNKNOWN. It does not derive motives from arbitrary action verbs, certify causality, insert prose, or rewrite any candidate. Complete prose survives absent or inaccurate optional metadata. A tiny explicit whole-clause/copula-negation check identifies only directly asserted literal contradictions; all other semantic changes stay unresolved. This is not a new semantic scoring system.

`proposed_story_authoring_contract` documents a disabled responsibility split using existing STORY candidate fields. It is not called by the live prompt compiler or dispatch path. No new response-schema version or migration was introduced.

| Responsibility | Current real request | Proposed, NOT ACTIVATED |
|---|---|---|
| Narrative | Model writes two complete stories | Same |
| Creative intent / pacing / risks | Model provides summaries and lists | Same, explicitly author intentions rather than verified evidence |
| Protected facts | Model copies locked clauses and self-maps source/candidate quotes | Source remains authoritative; server mechanically derives literal spans; nontrivial preservation stays UNKNOWN |
| Evidence certification | Generator asserts SOURCE_COMPLIANT + exact excerpts | Model no longer certifies its own evidence or supplies required sourceQuote copies |
| Meaning and creative merit | Paid reviewer unreachable unless all generator citations pass | Independent assessment only under a separately owner-approved admission policy; invalid citations excluded from evidence |
| Source approval / production | Explicit later operations | Same; never inferred from assessment |

Simplest prospective output keeps structured candidates and existing field names:

```json
{"alternatives":[{"candidateId":"candidate-1","title":"...","text":"complete authored narrative","proposedChanges":["..."],"motivation":"author intent, not a certified excerpt","progression":"intended pacing and development","weaknesses":["..."],"productionRisks":["..."],"sourceContract":{"protectedChanges":[]}}]}
```

The array must contain the authorized count; the example shows only the existing per-candidate shape. Exact duration remains authoritative production context rather than a model-certified fact. No provider JSON Schema is newly activated. No token-budget increase is proposed. A future author prompt should contain the source once, one clear lock/revision matrix and concise creative objectives; duplicative exact-quote self-certification should move to the application. Removing score-heavy prompt-only eligibility context from a future authoring projection is an audit recommendation, not a change to saved canonical records or current paid instructions.

## Statuses and owner policy boundary

| Proposed status | Meaning | Current paid eligibility |
|---|---|---|
| DETERMINISTIC_SOURCE_CONTRACT_PASSED | All protected literal clauses located; meaning still UNKNOWN | False; unchanged existing gate remains authority |
| SEMANTIC_FIDELITY_REVIEW_REQUIRED | Bounded narrative exists; some protected meaning needs assessment | False; future assessment-only policy requires explicit owner decision |
| PROTECTED_CHANGE_PROPOSAL | Explicit proposed protected change, not an approved source | False; separate source decision required |
| DEFINITE_SOURCE_VIOLATION | Only directly detected literal contradiction in extractor; broader forensic violations separately annotated | False |
| INVALID_GENERATION_OUTPUT | Missing/invalid narrative/identity/title structure or malformed proposal | False |

Potential future consideration applies to complete, source-bound narratives with no known definite contradiction/protected-change bypass. It is **not** an admission grant. The owner would need to approve assessment of source-UNKNOWN narratives using genuine candidate text plus server-derived evidence, while excluding invalid model citations and preserving all source flags. The reviewer could fail fidelity or creative merit; it could never approve a source revision, prompt or render. No paid command or fallback path was added here. In particular, these pure proposal results cannot make an old failed run resumable or reuse an old spending authorization.

A second focused correction was justified by the regression audit: `story_quality` let raw action vocabulary override its existing normalized synonym event path and classified pull/yank/remove paraphrases as PARTIALLY_DISTINCT. The existing failing near-duplicate regression reproduced it. When the supported normalized causal path is identical, the diagnostic now treats that as a structural match. This conservatively limits superficial-variation claims; it does not establish semantic fidelity/material improvement, change canonical scoring or widen paid admission. Historical server-added storyQuality diagnostics remain frozen; the original raw provider output did not include those server diagnostics.

# F. Four-response offline replay

| Authentic narrative | Original live/request reason | Original strict source result | Proposed narrative/evidence separation | Forensic limit / recommendation |
|---|---|---|---|---|
| Call 1 / candidate 1 | Requested/returned model mismatch; live source gate not reached | Subsequent offline UNKNOWN, summary fields and protected mappings unsupported | Narrative valid; two invalid excerpt claims; SEMANTIC_FIDELITY_REVIEW_REQUIRED; all paid flags false | Retreat-trigger deviation remains; do not pass it as faithful |
| Call 1 / candidate 2 | Same identity mismatch | Subsequent offline UNKNOWN, summary fields and protected mappings unsupported | Narrative valid; two invalid excerpt claims; semantics UNKNOWN; all paid flags false | Sit-down/refusal has a concrete creative hypothesis; fidelity/pacing unresolved |
| Call 2 / candidate 1 | SOURCE gate | SOURCE_VIOLATION: continuity citation absent | Narrative valid; one invalid citation; semantics UNKNOWN; all paid flags false | Removal-directed actions and simpler ending business merit controlled criticism |
| Call 2 / candidate 2 | SOURCE gate | Same absent continuity citation | Narrative valid; one invalid citation; semantics UNKNOWN; all paid flags false | Clap-to-crush trigger and wardrobe/production details unresolved |

Original responses/receipts/admission outcomes are unchanged. The new status is a **proposed offline analysis result**, not a revised historical result or approved source fidelity. All four narrative SHAs remain exact. The implementation is verified for mechanical extraction; its paid-admission policy remains PROPOSED/disabled.

# G. Actual verification

The 17 new proposal/extraction tests cover exact present quotes; absent exact quote with possible continuity; absent quote with explicit contradiction; false compliance labels; paraphrase and physical-rule substitution; missing protected ending; explicit change proposals; distinct versus duplicated narratives; source-permitted unresolved endings; immediate curiosity without impossible-physics opening; incomplete metadata with complete narrative; complete metadata with invalid narrative; incorrect supplied offsets; immutable real responses; no provider construction; and no source/render/paid approval from structural status. The four-story replay uses all four authentic texts, not authored replacement fixtures.

Initial broader regression: **212 passed, 1 failed, exit 1**. The failure was the existing synonym-paraphrase diversity test described above. After the minimal normalized-path correction, the identical full command passed **213 tests, exit 0**, with 343 existing warnings. Final ML command and exact results are in [test-results.json](deepseek-story-root-cause-evidence/test-results.json).

Final Java command `mvn -q -Dtest=StoryExperimentContractTest,StoryEvolutionServiceTest,StoryReviewIndependenceTest test`: **40 passed, zero failures/errors/skips, exit 0** (33 pilot, 5 service, 2 independence). It uses disposable PostgreSQL, real owner-scoped service/ledger and signed FastAPI boundaries with mocked SDK transports. The new saved-first/saved-followup cases each replay both authentic narratives, verify unchanged raw bytes and strict STOPPED outcome, derive separate reports, verify no second reservation and no source approval, then attempt reprocessing and confirm no replay. The historical first-run identity mismatch is not retried; its saved response is used only as mocked data in a hypothetical offline exact-Flash test grant.

The existing positive fixture E2E still completes two mocked requests, preserves their durable provenance and ends with owner approval pending; it is technical evidence, not a real creative result. The new disabled proposal cannot bypass current admission. Existing F8, canonical stability and creative-role regressions passed. No Ruleset 1.11 weights, thresholds or scoring code were changed.

Evidence traces:

- [Four authentic narrative/evidence analyses](deepseek-story-root-cause-evidence/four-authentic-story-replay.json)
- [Positive mocked E2E](deepseek-story-root-cause-evidence/story-root-cause-positive-dry-run.json)
- [First saved-response PostgreSQL/HTTP replay](deepseek-story-root-cause-evidence/story-root-cause-saved-first.json)
- [Follow-up saved-response PostgreSQL/HTTP replay](deepseek-story-root-cause-evidence/story-root-cause-saved-followup.json)
- [Disabled authoring responsibility proposal](deepseek-story-root-cause-evidence/proposed-authoring-responsibilities.json)

# H. Next action and exact required decision

**REUSE_EXISTING_STORIES_FOR_SEPARATELY_AUTHORIZED_INDEPENDENT_REVIEW.** Do not pay for another generation now. The most defensible recoverable material is the sit-down/refusal proposal in first-call candidate 2 and the removal-directed/held-stop proposal in follow-up candidate 1. Both have specific creative hypotheses and unresolved fidelity/feasibility; neither is approved or demonstrated superior. The other two should remain visible as counterexamples, especially the retreat-trigger case.

Before any future paid assessment, the owner must explicitly approve a narrow **assessment-only admission policy**: complete authentic narratives with UNKNOWN source semantics may be independently assessed using their original text, exact server-derived evidence and visible citation failures; known definite violations and protected-change proposals remain blocked or require separate source decisions. Invalid model citations stay invalid. A reviewer must decide semantic fidelity before any positive creative recommendation is actionable. Source approval, BUILD_PROMPT and production remain separate. A fresh request-specific spending authorization would then be required. Neither policy approval nor spending authorization was granted by this task, and no paid experiment manifest was prepared.

This recommendation recovers value from existing model-authored material while honestly testing the unresolved question: whether a plausible action/stopping change is better for viewers. It does not infer strong creativity from schema compliance, word diversity or a canonical A. If independent assessment finds no material gain, KEEP_EXISTING_SOURCE is the correct outcome. If the protected engine/ending is the limiting factor, the next decision should be an explicit exploration proposal scope rather than more exact-quote prompt retries.

# Boundaries, files and Git observation

Changed production files: `intelligence/ml-service/app/workflow/story_evidence.py` (additive offline extractor/proposal) and `story_quality.py` (conservative synonym-path diagnostic). Changed tests: `test_story_evidence_responsibility_split.py`, `story_experiment_bridge.py`, and existing Java `StoryExperimentContractTest.java`. No live prompt instructions, strict validate(), HMAC, model identity/budget checks, source locks, paid-review gate, approvals, provider configuration, database schema or endpoint were changed. No new service, framework, schema version, provider probe, deployment, image/video generation or publication was performed.

Git HEAD at start: `324f414f6131b7585eac8dd809937c371f50e6ac`; observed during work: `5b70c718fa885fe181cdfc7bc460abc930a04dae`; at report creation: `5b70c718fa885fe181cdfc7bc460abc930a04dae`. History movement was independently observed; its actor is not attributed without evidence. No agent commit/amend/reset/push was issued, and no external changes were reverted.

The task ends with zero new provider requests/spending, all original artifacts unchanged, and no new paid authorization.

Final integrity verification observed another HEAD, `92864f46b68ed9027d88fb1081f4bb5eb9c93a50`. The actor remains unattributed; the agent performed no history mutation. All 33 historical evidence hashes, all four narrative hashes and all report links passed final verification.
