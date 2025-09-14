# Career Coach Agent System Plan

## 1. High-Level Goals
- Private 1:1 CareerCoach agent (audience = you).
- Capabilities: career strategy, situational coaching, job hunt pipeline, application tailoring, interview prep, company intelligence.
- Delegation: specialized sub‑agents/tools for job discovery, job/profile matching, company research.
- Guardrails: no fabrication; cite sources (resume, LinkedIn export, GitHub repos, web search snippets).

## 2. Proposed Agents
1. **CareerCoach** (orchestrator + dialog manager)
   - Intake user goals / concerns.
   - Plans next steps (invoke tools or delegate).
   - Synthesizes recommendations with reasoning + action checklist.
2. **JobDiscoveryAgent**
   - Queries job sources (APIs, RSS, scraped exports, user‑pasted JD).
   - Normalizes job descriptions → structured schema.
3. **ProfileMatchAgent**
   - Compares your profile vs a job (skills, impact signals, gaps).
   - Produces: match score, missing competencies, tailoring levers.
4. **CompanyResearchAgent**
   - Web search + news + engineering blog + GitHub org signal.
   - Extracts culture cues, recent funding, product shifts, interview topics.
5. **(Optional later) InterviewPrepAgent**
   - Generates role-specific prep map: likely questions, STAR story prompts.
6. **Tool Layer (not agents):**
    - resume_retriever, linkedin_retriever, github_repo_indexer
    - web_search (use opensource tool/library)
    - job_search (reusing existing DuckDuckGo ATS scraper)
    - profile_match (wrap existing job_match algorithm + LLM layer)
    - agents_runtime (OpenAI Agent SDK orchestrator + tool registration)

## 3. Interaction Modes (Workflows)
A. **Ad‑hoc coaching:** User describes situation → Coach clarifies → structured plan (perspective, options, next actions).
B. **Job targeting:** User pastes JD or triggers discovery → DiscoveryAgent returns normalized jobs → Coach asks which to pursue → MatchAgent runs → Coach returns strategy + tailoring guidance.
C. **Company research:** User names company → ResearchAgent gathers facts → Coach turns into narrative + networking angle + question bank.
D. **Application tailoring:** Provide base resume section + job → MatchAgent gap map → Coach outputs bullet rewrites + cover letter scaffold.
E. **Progress tracking:** Coach logs commitments; periodic follow-up (pull from note_store).

## 4. Directory Layout (new repo: `career-coach-ai`)
TODO

## 5. Key Schemas
- **JobPosting:** {id, title, company, raw_text, normalized_skills[], location, source_url} -> See job_search.py
- **SkillAssessment:**  REUSE SkillAssessment in models/job_match.py
- **JobMatchResult:** REUSE JobMatchResult in models/job_match.py
- **CompanyIntel:** {company, summary, recent_events[], culture_signals[], tech_stack[], sources[]}
- **CoachingNote:** {timestamp, topic, commitments[], sentiment, follow_up_date}
- **JobSearchResults:** See job_search.py

## 6. Planning & Delegation
- CareerCoach uses a lightweight planner: decide(action_sequence) → tool calls / sub‑agent calls.
- Keep a reasoning scratchpad internal (not exposed unless user asks).
- Use structured output JSON for each sub‑agent; Coach consumes and verbalizes.


## 7. Prompting Patterns
- System prompt (Coach): identity, boundaries (no external claims w/o citation), coaching style (Socratic when clarifying).
- Role prompts per sub‑agent (match, research).
- Planner prompt: Given user_turn + memory_summary → produce plan: [{step, target_agent/tool, rationale}].
- Always enforce: “If lacking data, ask clarifying question first.”

Example `coach_system.md` snippet:
````markdown
You are an expert career and job search coach assisting only the user (the professional).
You know their background from provided documents and other sources.
Never fabricate experience or employer names. Cite sources: [resume], [linkedin], [repo:<name>], [web:<domain>].
Style: concise, actionable, empathetic, bias-aware. Default goal: increase clarity → propose next best action.
If plan requires external info, request permission before running web/company research tools.
````

### !!!IMPORTANT!!! OpenAI Agent SDK Integration
Instead of manual low-level OpenAI calls, we register tools with the OpenAI Agent SDK. The CareerCoach runs as a primary Assistant with tool definitions; sub-agents become either (a) separate Assistants invoked programmatically or (b) pure Python tools surfaced to the primary Assistant.
Potntially use Agent.as_tool() or just use the tools directly depending on the use case.
Use Handoff if suitable.

Registered tool set (initial):
1. `profile_match_tool` – input: {job_text}; output: `JobMatchResult` JSON.
2. `job_search_tool` – input: {title, keywords?, limit?}; output: List[`JobSearchResults`].
3. `company_research_tool` – input: {company, depth?}; output: `CompanyIntel`.
4. `retrieve_context_tool` – input: {query, k}; output: chunks with source tags.
5. `notes_tool` – CRUD for coaching notes (log / list / upcoming commitments). - Probably skip this for now.

Each tool returns strictly schema-validated JSON; Assistant prompt instructs to cite only fields present and include source tags.

## 9. MVP Phases
**Phase 1 (Core)**
GOAL: Gradio chat interface for coaching. Implement the coaching intent.
The coach should be able to see the user's profile, resume, and other sources of information and able to Q&A with the user.
- New folder "career-coach-ai" with project structure. Use UV for project creation and use a python virtual environment.
- Load profile docs + resume  + chunk embeddings.
- CareerCoach agent with simple intent classification: {coaching, job_analysis, company_research, application_help}.

**Phase 2**
GOAL: Implement the job_analysis intent.
- User provides a job posting in chat.
- JobAnalysisAgent analyzes the job posting and provides a detailed analysis if match is above a certain threshold. (e.g Good or better)
- The coach should be able to see the job analysis and able to Q&A with the user, and offer recommendations, next steps, and other guidance.

**Phase 3**
GOAL: Implement the company_research intent.
- User provides a company name in chat.
- CompanyResearchAgent gathers facts about the company and provides a detailed analysis.
- The coach should be able to see the company research and able to Q&A with the user, and offer recommendations, next steps, and other guidance.

**Phase 4**
GOAL: Implement the application_help intent.
-  If user decides to apply (e.g after a job analysis)
- ApplicationHelpAgent provides a detailed analysis of the application process, including how to tailor the resume, cover letter, and other materials to the job.
- The coach should be able to see the application help and able to Q&A with the user, and offer recommendations, next steps, and other guidance.


**Phase 5**
- Evaluation harness (hallucination check, citation coverage, actionability score).
- Use existing evaluator.md
- Implement feedback mechanism for the coach to improve the response.

**Phase 6**
GOAL: Implement the interview_prep intent. (Optional)


## 11. Tool Selection Logic (Simplified)
- If user asks “Should I apply?” and provides JD → run match → return strategy.
- If user asks “Tell me about Company X” → confirm permission → company_research.
- If user expresses vague stress / situation → ask 1–2 clarifiers before advising.
- If repeated topic last 24h and no progress → surface previous commitments and ask status.


## 12. Reuse From Existing Project
- Reuse promptkit renderer.
- Reuse evaluation style (adapt evaluator.md for coaching).
- Reuse GitHub repo summarization logic.
- Reuse `models/job_match.py` SkillAssessment & JobMatchResult schemas directly (import, do not duplicate).
- Reuse `job_search/job_search.py` logic by factoring into `tools/job_search_tool.py`.
- Reuse any existing structured evaluation patterns for grounding (apply to coaching responses).
- Reuse job/profile matching logic.

## 15. Next Concrete Tasks
TBD
