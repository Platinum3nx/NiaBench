# NiaBench

Context Retrieval Benchmark for AI Coding Agents

Product Requirements Document · v1.0

Status: Draft · Target launch: 3 days from start

|                      |                                                                     |
|----------------------|---------------------------------------------------------------------|
| **Field**            | **Detail**                                                          |
| **Project**          | NiaBench — Open-source hallucination benchmark for AI coding agents |
| **Author**           | \[Your name\] — independent builder                                 |
| **Primary audience** | Arlan Rakhmetzhanov (Nozomio), AI developer community, YC ecosystem |
| **Target repo**      | github.com/\[you\]/nia-bench (public from Day 1)                    |
| **Target site**      | niabench.dev (or contextbench.dev)                                  |
| **Budget**           | \~$35–45 total API costs (Anthropic + OpenAI + E2B)                 |
| **Build time**       | 2.5–3 focused days with OpenClaw overnight delegation               |

## 1. Overview

### 1.1 Purpose

NiaBench is a public, reproducible benchmark that measures how much AI coding agents improve when given access to fresh, indexed documentation context via Nia (Nozomio's context retrieval API). It directly validates Nozomio's core product thesis: that context — not generation — is the bottleneck in AI-assisted software development.

The benchmark addresses a significant credibility gap in the market. Nozomio currently cites a self-reported 27% improvement in Cursor performance from internal evaluations. NiaBench produces a third-party, open-source, fully reproducible version of that claim — across 150+ tasks, two frontier models, and 20 high-churn libraries. This is the kind of artifact that gets cited in VC decks, shared by AI newsletter authors, and referenced in developer communities.

### 1.2 Strategic Goals

-   Provide Nozomio with credible, third-party benchmark data validating their core product claim

-   Demonstrate deep technical understanding of the context retrieval problem to Arlan Rakhmetzhanov

-   Create a durable open-source resource that stays current as libraries evolve

-   Establish the builder as a serious contributor to the AI developer tooling ecosystem

-   Generate organic developer community interest through a public launch on X/Twitter and GitHub

### 1.3 Non-Goals

-   This is not a general LLM coding benchmark (not competing with HumanEval, SWE-bench, etc.)

-   This is not a product for end users — it is research infrastructure and a community resource

-   This does not evaluate Nia's latency, pricing, or reliability — only its impact on context quality

-   This does not benchmark models against each other — the comparison is always with-Nia vs without-Nia for the same model

### 1.4 Success Criteria

|                                          |                           |                   |
|------------------------------------------|---------------------------|-------------------|
| **Metric**                               | **Target**                | **Stretch**       |
| Arlan responds publicly to launch thread | Yes, within 48 hrs        | Retweets / shares |
| GitHub stars in first week               | 50+                       | 200+              |
| Tasks in dataset at launch               | 150                       | 200               |
| Libraries covered                        | 20                        | 30                |
| Measured Nia improvement delta           | Statistically significant | &gt;25% overall   |
| Dashboard live and indexed by Google     | Within 24 hrs of launch   | —                 |

## 2. Problem Statement

### 2.1 The Hallucination Problem in Coding Agents

Modern AI coding agents (Cursor, Claude Code, Cline, Continue) rely on LLM training data that has a fixed cutoff date. Software libraries, however, evolve continuously — APIs change, methods are deprecated, import paths shift, configuration schemas are restructured. The result is a systematic failure mode: agents confidently produce code using patterns that are months or years out of date.

This is not a model quality problem — it is a context problem. A model that was state-of-the-art at training time will produce deprecated LangChain, tRPC, or Prisma code not because it is unintelligent, but because it has never seen the new API. Given fresh documentation, the same model produces correct code.

### 2.2 The Measurement Gap

Nozomio claims Nia solves this problem by providing coding agents with continuously indexed, up-to-date context from documentation sites, GitHub repositories, and research papers. Their internal evaluations show a 27% improvement in Cursor performance after Nia integration.

> *The problem: there is no public, reproducible, methodology-transparent benchmark that validates this claim. The developer community has no way to independently verify the improvement, understand which libraries benefit most, or trust the headline number.*

NiaBench fills this gap. It is the benchmark Nozomio should have built themselves, built instead by an independent developer — which makes it more credible.

### 2.3 Why This Matters to Arlan

-   Marketing ammunition: a reproducible third-party benchmark is far more shareable than internal claims

-   Sales enablement: enterprise customers evaluating Nia need external validation

-   Product roadmap signal: per-library breakdown reveals which integrations drive the most value

-   Community credibility: open-source benchmarks attract contributors, users, and press coverage

## 3. System Architecture

### 3.1 Component Overview

NiaBench consists of four interconnected components that form a complete evaluation pipeline, plus a public-facing dashboard layer.

|                          |                                                        |                                       |
|--------------------------|--------------------------------------------------------|---------------------------------------|
| **Component**            | **Responsibility**                                     | **Key technology**                    |
| **Task Dataset**         | 150+ benchmark tasks with structured metadata          | JSON, OpenClaw-assisted generation    |
| **Eval Harness**         | Runs each task with and without Nia context            | Python, Nia API, Anthropic/OpenAI API |
| **Grading Pipeline**     | Scores outputs via sandbox execution and LLM-as-judge  | E2B sandboxes, Claude-as-judge        |
| **Dashboard**            | Public-facing results site with per-library breakdowns | Next.js, Tailwind CSS, Vercel         |
| **Auto-update Pipeline** | Monitors library releases, generates new tasks         | GitHub Actions, OpenClaw, Claude API  |

### 3.2 Data Flow

The evaluation pipeline operates as follows: for each task in tasks.json, the harness makes two LLM calls using identical prompts and model parameters. The baseline call receives only the task description. The treatment call receives the task description plus context chunks retrieved from Nia's search API for the relevant library and version. Both outputs are saved with full metadata including exact prompts, retrieved context, model, temperature, and timestamp.

Each output then passes through the grading pipeline. For tasks that generate executable code, the output is passed to an E2B sandbox which installs the task-specific library version, executes the code, and captures the result. For all tasks, Claude-as-judge evaluates both outputs against a task-specific rubric and produces a structured score with a one-sentence rationale. The CompositeGrader combines execution results (60% weight) and judge scores (40% weight) into a final per-task score.

Aggregate scores are computed per library and overall, then written to scores.json which the dashboard reads at build time for static generation.

### 3.3 Repository Structure

|                             |                                                 |
|-----------------------------|-------------------------------------------------|
| **Path**                    | **Contents**                                    |
| **/dataset/tasks.json**     | Master benchmark task file                      |
| **/dataset/rubrics.json**   | Per-category grading rubrics for LLM judge      |
| **/harness/run\_eval.py**   | Main evaluation entry point                     |
| **/harness/nia\_client.py** | Nia API wrapper with local caching layer        |
| **/grading/sandbox.py**     | E2B SandboxGrader class                         |
| **/grading/judge.py**       | Claude-as-judge JudgeGrader class               |
| **/grading/composite.py**   | CompositeGrader combining both signals          |
| **/results/**               | Raw eval outputs, gitignored except scores.json |
| **/dashboard/**             | Next.js application                             |
| **/.github/workflows/**     | Auto-update and CI workflows                    |

## 4. Task Dataset

### 4.1 Task Schema

Every benchmark task is represented as a JSON object conforming to the following schema:

```json
{
  "id": "langchain-py-0031",
  "library": "langchain-python",
  "version_introduced": "0.3.0",
  "task_description": "Write a function that initializes...",
  "deprecated_pattern": "from langchain.chat_models import ChatOpenAI",
  "correct_pattern": "from langchain.chat_models import init_chat_model",
  "reference_solution": "...",
  "difficulty": "medium",
  "category": "api-migration",
  "executable": true,
  "why_models_fail_this": "Training data predates v0.3 release..."
}
```

### 4.2 Target Libraries

The initial dataset covers 20 libraries selected for high churn rate, large developer mindshare, and significance to AI/ML and web development — the two domains most relevant to Nozomio's customer base.

|                              |               |                                               |
|------------------------------|---------------|-----------------------------------------------|
| **Library**                  | **Min tasks** | **Why it's included**                         |
| **Vercel AI SDK**            | 10            | High churn, core to AI app development        |
| **LangChain Python**         | 10            | Major v0.2→v0.3 migration, widely used        |
| **LangChain JS**             | 8             | Parallel breaking changes to Python version   |
| **LlamaIndex**               | 8             | Major API restructure, AI infra staple        |
| **HuggingFace Transformers** | 8             | Continuous API evolution, massive mindshare   |
| **tRPC**                     | 8             | v10→v11 breaking changes, popular in Next.js  |
| **Prisma**                   | 8             | Schema and client API changes, widely adopted |
| **Drizzle ORM**              | 7             | Rapid evolution, growing adoption             |
| **NextAuth / Auth.js**       | 8             | v4→v5 major migration, confusing for agents   |
| **Anthropic SDK**            | 7             | Directly relevant to Nia's audience           |
| **OpenAI SDK**               | 7             | v3→v4 breaking changes, ubiquitous            |
| **TanStack Query v5**        | 7             | Large API surface, major v4→v5 migration      |
| **TanStack Router**          | 6             | Newer library, rapidly changing               |
| **Supabase JS**              | 6             | Auth and client API changes                   |
| **Zod**                      | 6             | v3→v4 migration underway                      |
| **Shadcn/ui**                | 6             | Component API and import path changes         |
| **HuggingFace Diffusers**    | 6             | Pipeline API evolution                        |
| **Effect-TS**                | 5             | Niche but high agent failure rate             |
| **Upstash Redis SDK**        | 5             | Serverless-native, growing use in AI stacks   |
| **Radix UI**                 | 5             | Component API changes, widely used            |

### 4.3 Task Categories

|                    |                                                |                  |
|--------------------|------------------------------------------------|------------------|
| **Category**       | **Description**                                | **% of dataset** |
| **api-migration**  | Use new API that replaced a deprecated one     | 45%              |
| **import-path**    | Correct import location after restructure      | 20%              |
| **config-schema**  | Write config using new schema format           | 15%              |
| **type-signature** | Match updated TypeScript types or Python types | 10%              |
| **best-practice**  | Use current recommended patterns               | 10%              |

### 4.4 Task Quality Standard

Every task in the dataset must pass the following quality gate before inclusion:

1.  A model without Nia context would confidently produce the deprecated pattern — not a guess, a confident wrong answer

2.  The task is phrased as natural developer language, not a test question or academic prompt

3.  The deprecated pattern and correct pattern are both explicitly documented in the task metadata

4.  The version boundary is precise — the task specifies exactly which version introduced the change

5.  For executable tasks, a reference solution exists that passes execution in a clean environment

## 5. Evaluation Harness

### 5.1 Core Design Principles

-   Reproducibility: every run must be fully reproducible given the same task ID, model, and date. Nia responses are cached locally keyed by task ID to prevent context drift between runs

-   Isolation: baseline and treatment calls use identical parameters (model, temperature=0, same system prompt) — the only variable is whether Nia context is injected

-   Transparency: every output file contains the full prompt sent, not just the response. Anyone can audit exactly what the model received

-   Provenance: results are versioned by run ID and never overwritten — reruns create new result files

### 5.2 Baseline Call

The baseline call is the ground truth for model performance without external context. The system prompt is minimal and consistent across all tasks: it identifies the model as a coding assistant and instructs it to produce only code without explanation. The user prompt is the task description verbatim from tasks.json.

> *Temperature is locked at 0 for all eval calls to ensure determinism. This is a non-negotiable constraint — any temperature above 0 makes results non-reproducible.*

### 5.3 Treatment Call (with Nia)

The treatment call receives the same system and user prompts as the baseline, plus a context block injected between them. This context block is retrieved from Nia's search API using a query derived from the task's library, version, and category fields. The retrieved chunks are formatted as a clearly labeled section: CURRENT DOCUMENTATION CONTEXT (retrieved via Nia) followed by the chunks separated by triple dashes.

The context injection point is the system prompt — not the user prompt and not appended after the task. This matches how Nia is actually used in production via MCP, ensuring the benchmark reflects real-world behavior.

### 5.4 Output Schema

Each task produces a result file with the following structure:

-   task\_id, library, version\_introduced, category, difficulty

-   model, temperature, run\_id, timestamp

-   baseline\_prompt (full), baseline\_response, baseline\_tokens\_in, baseline\_tokens\_out

-   nia\_context\_retrieved (full chunks), nia\_query\_used, nia\_response\_time\_ms

-   treatment\_prompt (full), treatment\_response, treatment\_tokens\_in, treatment\_tokens\_out

-   sandbox\_result (if executable): executed, exit\_code, stdout, stderr, error\_type

-   judge\_result: baseline\_score (0-2), treatment\_score (0-2), baseline\_rationale, treatment\_rationale

-   composite\_score: baseline\_final, treatment\_final, delta

## 6. Grading Pipeline

### 6.1 E2B Sandbox Grader

#### Architecture

Each executable task runs in a fresh E2B sandbox — no shared state between tasks. The sandbox receives the task's target library version and installs it as a first step using uv for speed. Code execution is wrapped in a 15-second timeout. The grader captures exit code, stdout, stderr, and classifies failures into typed error categories.

#### Error taxonomy

|                     |                                                                                     |
|---------------------|-------------------------------------------------------------------------------------|
| **Error type**      | **What it signals**                                                                 |
| **ImportError**     | Model used a module path that no longer exists — strong signal of deprecated import |
| **AttributeError**  | Model called a method that was renamed or removed — core hallucination type         |
| **TypeError**       | Model used wrong argument signature — API signature changed                         |
| **ValidationError** | Model produced invalid config schema — schema migration failure                     |
| **Timeout**         | Execution hung — likely infinite loop or blocking call                              |
| **ParseError**      | Model output was not valid code — markdown leakage or malformed output              |

Error taxonomy is analytically valuable beyond the pass/fail score — the public dashboard surfaces error type breakdowns, showing that Nia reduces AttributeError and ImportError specifically, which maps directly to the version-drift problem.

### 6.2 LLM-as-Judge

#### Judge prompt structure

Claude (claude-sonnet) acts as judge for all tasks. The judge receives: (1) the task description, (2) the reference solution if available, (3) the baseline model output, (4) the treatment model output, and (5) the rubric for this task category. It returns a structured JSON object with scores and rationales.

#### Scoring rubric

-   Score 2 — Correct and idiomatic: uses the current API, correct import path, no deprecated patterns, would work as-is

-   Score 1 — Partially correct: uses roughly correct logic but includes at least one deprecated pattern, wrong import, or outdated method name

-   Score 0 — Confidently wrong: uses a pattern that would fail on the target version, or completely misses the API

> *The rationale field is mandatory and must be one specific sentence identifying exactly what is correct or incorrect. Generic rationales ('the code looks correct') are not acceptable and trigger a retry.*

### 6.3 Composite Scoring

The CompositeGrader combines sandbox and judge scores as follows:

-   For executable tasks: composite = (sandbox\_binary × 0.6) + (judge\_score\_normalized × 0.4)

-   For non-executable tasks: composite = judge\_score\_normalized (1.0 weight)

-   sandbox\_binary: 1.0 if exit\_code == 0, else 0.0

-   judge\_score\_normalized: judge\_score / 2.0 (maps 0-2 scale to 0.0-1.0)

This weighting reflects the relative reliability of each signal. Code execution is objective and binary — it either works or it doesn't. The judge score adds nuance for partial correctness but is downweighted to avoid over-relying on a single model's judgment.

## 7. Dashboard

### 7.1 Design Philosophy

The dashboard must feel like a legitimate research artifact, not a portfolio project. The reference aesthetics are evals.anthropic.com and scale.com/leaderboard — clean, data-dense, typographically disciplined. It must be immediately comprehensible to a developer who lands on it from a tweet, and it must be designed to be screenshot-shareable (the library leaderboard table in particular).

### 7.2 Pages and Components

#### Hero page

-   Three primary stats displayed prominently: overall accuracy without Nia, overall accuracy with Nia, improvement delta as a percentage with directional arrow

-   Secondary stats: tasks evaluated, libraries covered, models tested, last updated timestamp

-   Library leaderboard table below the fold: columns are library, tasks, without-Nia score, with-Nia score, delta (color-coded bar), best improvement example

-   Table is sortable by delta — default sort is descending delta so most dramatic improvements surface first

-   A one-paragraph methodology summary with a link to the full methodology page

#### Task drilldown page

-   Reached by clicking any row in the leaderboard or any individual task link

-   Shows: task description, library and version, category and difficulty tags

-   Side-by-side code comparison: baseline output (left) vs treatment output (right), syntax highlighted

-   Judge rationale displayed below each output with the 0/1/2 score visually indicated

-   Execution result shown if applicable: exit code, error type, stdout/stderr excerpt

-   A 'What changed in this version' callout linking to the library's changelog for this version

#### Methodology page

-   Full methodology description: dataset construction, harness design, grading approach

-   Explicit limitations section — what the benchmark does not measure

-   How to reproduce the results locally (step-by-step)

-   How to contribute new tasks (links to CONTRIBUTING.md)

### 7.3 Technical Stack

-   Framework: Next.js 14+ with App Router

-   Styling: Tailwind CSS

-   Data: results loaded at build time via static generation — no client-side API calls

-   Syntax highlighting: Shiki (handles more languages than Prism, better dark mode)

-   Deployment: Vercel, triggered automatically on push to main

-   Analytics: Vercel Analytics (free tier) — useful for showing Arlan that real developers are using it

## 8. Auto-Update Pipeline

### 8.1 Purpose

A benchmark that goes stale loses credibility. The auto-update pipeline ensures NiaBench stays current as libraries release new versions, automatically generating candidate tasks for human review when a breaking change is detected. This is a key differentiator from one-time research snapshots.

### 8.2 Workflow

1.  GitHub Actions workflow runs on weekly cron schedule

2.  For each library in the dataset, fetches the latest release tag from GitHub API

3.  Compares against the highest version currently in tasks.json

4.  If new version detected: triggers Claude API call with the release notes and changelog diff, asking it to identify breaking changes and draft 3-5 new benchmark tasks in the tasks.json schema

5.  Opens a GitHub PR with the draft tasks, titled 'Auto-generated tasks for \[library\] v\[version\]'

6.  PR description includes the raw changelog excerpt and the model's reasoning

7.  Human reviewer (you) approves, edits, or closes the PR

> *Full automation of task merging is intentionally avoided. Human review maintains quality standards and prevents garbage tasks from polluting the benchmark. The automation handles discovery and drafting; human judgment handles acceptance.*

## 9. Open Source Strategy

### 9.1 README Structure

The README is the primary marketing surface for the project. It must serve two audiences simultaneously: developers who want to use or contribute to the benchmark, and Arlan / investors who want to understand what was built and why. Structure:

1.  Badge row: stars, license, last-updated, task count

2.  One-paragraph abstract with the headline stat in bold

3.  Animated GIF or screenshot of the dashboard

4.  Quickstart: three commands to reproduce the full eval

5.  Results summary table (mirrors the dashboard library leaderboard)

6.  Methodology in plain English (not academic — readable)

7.  Limitations — honest, specific, written with confidence not defensiveness

8.  Contributing guide

9.  License (MIT)

### 9.2 CONTRIBUTING.md

Contributing a new task should take under 10 minutes for a developer who knows the library. The guide must include: the full task schema with field-by-field explanation, a worked example of a good task vs a poor task, the quality gate checklist, and how to submit (fork, add task, open PR with the task's library and version in the PR title). The bar for acceptance is deliberately documented as high — this signals seriousness.

### 9.3 License

MIT for code. The dataset (tasks.json) is released under CC BY 4.0 — this allows it to be cited in academic work and used in other benchmarks, which increases reach and credibility over time.

## 10. Launch Strategy

### 10.1 X/Twitter Thread Structure

The thread is the primary distribution mechanism. It should be written the evening before launch, reviewed fresh the next morning, and posted on a weekday between 9-11am SF time when Arlan is most likely to see it.

1.  Hook: 'AI coding agents are confidently wrong about APIs that changed 6 months ago. I wanted to know exactly how bad it is — and whether Nia fixes it. So I built a benchmark.' (no more than 280 chars)

2.  The problem: one specific example of a real failure — a task where GPT-4o without context uses the deprecated pattern with full confidence. Show the actual code output.

3.  The benchmark: what it is in two sentences. 150 tasks, 20 libraries, two frontier models, open source.

4.  The methodology: how it works in plain language. No jargon.

5.  The headline number: Nia improves accuracy by X% overall. With breakdown of top 3 libraries by improvement delta.

6.  The most surprising finding: one result that was counterintuitive or noteworthy.

7.  Call to action: 'The benchmark stays updated automatically as libraries release. Try it, add a task, or just tell me what I got wrong.' + repo link + site link

8.  Tag: @arlanrakh @nozomioai @ycombinator

### 10.2 Engagement Strategy

-   Reply to every substantive response within the first 6 hours — the algorithm rewards engagement velocity

-   If Arlan responds, engage with the content of his response before any mention of the internship — let the work speak first

-   Cross-post to relevant subreddits: r/LocalLLaMA, r/MachineLearning, r/webdev depending on framing

-   Submit to Hacker News with a Show HN post on day 2 once the thread has some traction

-   The internship ask, if needed, comes in a DM after public engagement — not in the thread itself

### 10.3 Timing

|                    |                                                                             |
|--------------------|-----------------------------------------------------------------------------|
| **When**           | **Action**                                                                  |
| Night before Day 1 | Brief OpenClaw. Buy domain. Create GitHub repo.                             |
| Day 3 evening      | Write X thread. Proofread README. Final deploy check.                       |
| Day 4 morning      | Read thread fresh. Tighten it. Post at 9-10am SF time.                      |
| Day 4 afternoon    | Monitor engagement. Reply to responses. Submit HN.                          |
| Day 5+             | DM to Arlan if no public response. Write blog post if significant traction. |

## 11. Risks and Mitigations

|                                                                |                                                                                         |                                                                                                                                                                   |
|----------------------------------------------------------------|-----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Risk**                                                       | **Impact**                                                                              | **Mitigation**                                                                                                                                                    |
| **E2B sandbox dependency hell**                                | Loses half of Day 2. Reduces benchmark credibility if execution results are unreliable. | Pre-test E2B with 5 tasks from different libraries before committing to full pipeline. Have Modal as fallback.                                                    |
| **Nia API rate limits during overnight run**                   | Delays results. May require paid plan upgrade.                                          | Email Arlan before starting. Implement exponential backoff. Local cache prevents duplicate calls.                                                                 |
| **Task quality too low**                                       | Benchmark can be dismissed as cherry-picked or too easy. Undermines credibility.        | Apply quality gate strictly during Day 1 review. Cut 20% of tasks rather than include weak ones.                                                                  |
| **Improvement delta too small or negative for some libraries** | Awkward if Nia makes things worse on some tasks. May require careful framing.           | Publish all results including negative ones — intellectual honesty increases credibility. Note which libraries Nia has indexed vs not.                            |
| **Arlan doesn't see the launch**                               | Primary outreach mechanism fails.                                                       | Email arlan@nozomio.com directly with a link on Day 4. Keep it one paragraph — link speaks for itself.                                                            |
| **OpenClaw task generation is low quality overnight**          | Loses Day 1 morning advantage. Manual curation takes longer.                            | Brief is highly specific (schema defined, examples given, quality criteria explicit). Worst case: spend Day 1 morning generating tasks manually with Claude Code. |

## 12. Appendix

### A. Environment Variables

|                         |                |                                  |
|-------------------------|----------------|----------------------------------|
| **Variable**            | **Required**   | **Source**                       |
| **NIA\_API\_KEY**       | Yes            | app.trynia.ai                    |
| **E2B\_API\_KEY**       | Yes            | e2b.dev/dashboard                |
| **ANTHROPIC\_API\_KEY** | Yes            | console.anthropic.com            |
| **OPENAI\_API\_KEY**    | For GPT-4o run | platform.openai.com              |
| **UPSTASH\_REDIS\_URL** | Optional       | upstash.com (Nia response cache) |

### B. Cost Estimates

|                             |                  |                   |                      |
|-----------------------------|------------------|-------------------|----------------------|
| **Item**                    | **Low estimate** | **High estimate** | **Notes**            |
| Claude eval run (150 tasks) | $4               | $6                | Sonnet 4.5           |
| Claude Code dev usage       | $15              | $25               | 3 days active dev    |
| Debug re-runs               | $3               | $8                | Partial runs         |
| GPT-4o comparison run       | $5               | $10               | OpenAI billing       |
| E2B sandbox execution       | $15              | $40               | \~300 sandboxes      |
| Domain (annual)             | $12              | $15               | Namecheap/Cloudflare |
| **Total**                   | **$54**          | **$104**          |                      |

### C. OpenClaw Brief Template

Copy this brief exactly when setting up the overnight task generation run:

```text
Task: Generate benchmark tasks for the NiaBench project.

For each of the following 20 libraries, crawl the GitHub releases
page and CHANGELOG.md. Extract every breaking change from the last
12 months. For each breaking change, generate a benchmark task in
this exact JSON schema: { id, library, version_introduced,
task_description, deprecated_pattern, correct_pattern, difficulty,
category, executable, why_models_fail_this }

Quality standard: only include tasks where a model trained before
the change would CONFIDENTLY produce the wrong answer. Ambiguous
tasks should be excluded. Minimum 8 tasks per library.

Save output to /dataset/tasks_raw.json
```
