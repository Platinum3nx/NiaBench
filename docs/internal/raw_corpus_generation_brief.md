# Raw Corpus Generation Brief

Use this prompt for bulk task generation.

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
- Each task must have a concrete before/after pattern.
- Keep prompts realistic, concise, and implementation-focused.
```
