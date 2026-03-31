# OpenClaw Brief

Use this prompt for the overnight draft task generation run.

```text
Task: Generate benchmark tasks for the NiaBench project.

For each of the following 20 libraries, crawl the GitHub releases
page and CHANGELOG.md. Extract every breaking change from the last
12 months. For each breaking change, generate a benchmark task in
this exact JSON schema: { id, library, version_introduced,
task_description, deprecated_pattern, correct_pattern,
reference_solution, difficulty, category, executable,
why_models_fail_this }

Libraries:
- Vercel AI SDK
- LangChain Python
- LangChain JS
- LlamaIndex
- HuggingFace Transformers
- tRPC
- Prisma
- Drizzle ORM
- NextAuth / Auth.js
- Anthropic SDK
- OpenAI SDK
- TanStack Query
- TanStack Router
- Supabase JS
- Zod
- shadcn/ui
- HuggingFace Diffusers
- Effect-TS
- Upstash Redis SDK
- Radix UI

Quality standard:
- Only include tasks where a model trained before the change would confidently produce the wrong answer.
- Exclude ambiguous changes, stylistic preferences, and weak migrations.
- Deprecated pattern and correct pattern must both be explicit.
- Use natural developer language, not exam language.
- Mark executable=true only if a clean reference solution can be run in an isolated environment.
- Minimum 8 tasks per library unless the library genuinely has fewer strong candidates.

Output:
- Save the raw output to /dataset/tasks_raw.json
- Return a JSON array only
```
