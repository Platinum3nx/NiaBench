# Contributing to NiaBench

Thank you for helping improve the benchmark.

## What a task must include

Each task in `dataset/tasks.json` must include:

- `id`
- `library`
- `version_introduced`
- `task_description`
- `deprecated_pattern`
- `correct_pattern`
- `reference_solution`
- `difficulty`
- `category`
- `executable`
- `why_models_fail_this`

The schema lives in `dataset/task.schema.json`.

## Quality bar

We only accept tasks that meet all of the following:

- a model without fresh context would confidently produce the wrong answer
- the change is real and version-specific
- the deprecated pattern and correct pattern are both explicit
- the prompt sounds like a real developer request
- executable tasks have a reference solution that can run cleanly

## Categories

- `api-migration`
- `import-path`
- `config-schema`
- `type-signature`
- `best-practice`

## Local validation

Run:

```bash
python3 scripts/validate_tasks.py dataset/tasks.json
```

To validate a raw draft file:

```bash
python3 scripts/validate_tasks.py dataset/tasks_raw.json
```

## Submission flow

1. Fork the repo.
2. Add or update tasks in `dataset/tasks.json`.
3. Run the validator.
4. Open a PR with the library and version in the title.
5. Include source links for the changelog, release notes, or docs that justify the task.

## What gets rejected

- vague “best practice” tasks without a crisp version change
- trivia that a model would only miss by chance
- tasks with no documented deprecated pattern
- tasks that are only stylistic preference
