# Stakeholder Walkthrough Notes (April 1, 2026)

## One-paragraph project summary

NiaBench is a reproducible A/B benchmark for coding models on version-sensitive library tasks. Each task is run twice under fixed settings: once without external context and once with Nia-retrieved documentation context. The benchmark is designed to be auditable: prompts, retrieved context, model outputs, judge outputs, and aggregates are all written to disk.

## One-paragraph methodology summary

The current locked pilot contains 30 tasks across 20 libraries. Two pinned models were run live (`gpt-4o-2024-11-20` and `claude-sonnet-4-20250514`), producing 60 evaluated rows. Scoring is judge-only for Layer 1 while sandbox execution remains deferred. Current aggregate snapshot from `results/scores.json`: without Nia `75.0`, with Nia `85.833333`, delta `+10.833333`.

## One-paragraph current state and next step

The benchmark now has real multi-model pilot evidence, validated aggregate contracts, and a reproducible dashboard deployment path. This release is intentionally scoped as the first credible benchmark build: locked `30`-task pilot, pinned models, and judge-only scoring while sandbox execution remains deferred. The immediate next step is sandbox integration so executable-task correctness is measured by both runtime behavior and rubric judgment, then widening the dataset from the expanded raw corpus.

## Representative examples for walkthrough

Suggested positive deltas:

- `openai-sdk-chatcompletions-to-responses` (`openai-sdk`)
- `anthropic-sdk-system-prompt-structure` (`anthropic-sdk`)

Suggested challenging deltas:

- `llamaindex-core-vector-index-import` (`llamaindex`)
- `effect-ts-package-unification-import` (`effect-ts`)

## Known limitations to state explicitly

- Scoring is judge-only for Layer 1.
- Sandbox integration is deferred.
- Retrieval rate limits can produce occasional empty-context treatment rows, with errors logged in artifacts.
