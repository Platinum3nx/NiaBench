# NiaBench Execution Board

Status: Draft  
Build window: 3 days  
Launch follow-through: Day 4 morning posts

## Hard Gates

- [ ] OpenClaw starts the night before Day 1, in parallel with setup, so the first morning begins with a draft dataset instead of a blank slate.
- [ ] The pilot is fixed at exactly `30 tasks`: all `20 libraries` represented, `10` libraries get a second task, and the set is balanced across `easy`, `medium`, and `hard`.
- [ ] The auto-update pipeline ships on Day 3 before launch; it is part of the launch story, not a post-launch enhancement.
- [ ] Before any large eval run, send Arlan a short email asking about rate limits for roughly `300` Nia API calls.

## Day 0 Evening

### Goal

Remove external blockers, set the repo foundation, and kick off dataset generation overnight.

### Requirements

- [ ] Library list confirmed
- [ ] Repo available
- [ ] Willingness to create accounts and provide keys

### Codex Owns

- [ ] Scaffold the repo
- [ ] Define schemas
- [ ] Add `.env.example`
- [ ] Draft the OpenClaw brief
- [ ] Build task validators
- [ ] Draft the one-paragraph email to Arlan

### You Own

- [ ] Send the email to `arlan@nozomio.com`
- [ ] Provide or create `NIA_API_KEY`
- [ ] Provide or create `E2B_API_KEY`
- [ ] Provide or create `ANTHROPIC_API_KEY`
- [ ] Provide or create `OPENAI_API_KEY`
- [ ] Start the OpenClaw run
- [ ] Buy and connect the domain if handling that early

### Done When

- [ ] `dataset/tasks_raw.json` is being generated overnight
- [ ] Repo skeleton exists
- [ ] API and account blockers are known

## Day 1 Morning

### Goal

Turn the overnight OpenClaw output into a credible draft dataset and wire the core eval harness.

### Requirements

- [ ] OpenClaw output is ready
- [ ] API keys are available
- [ ] Target models are decided

### Codex Owns

- [ ] Review and normalize raw tasks
- [ ] Cut weak tasks aggressively
- [ ] Implement `dataset/tasks.json` validation
- [ ] Build `harness/run_eval.py`
- [ ] Build `harness/nia_client.py` against Nia's direct `search` and `index` API
- [ ] Extract context chunks programmatically from Nia responses
- [ ] Inject retrieved context into the system prompt as a clearly labeled block
- [ ] Log the retrieved context chunks verbatim in the result file
- [ ] Log the full prompt sent in the result file

Implementation note: the harness must call Nia's `search` and `index` API directly, not via the MCP server. The MCP path adds indirection that makes context injection unauditable and must not be used for the harness under any circumstances.

### You Own

- [ ] Make final judgment calls on borderline tasks where benchmark credibility is subjective
- [ ] Confirm model scope if there is any ambiguity

### Done When

- [ ] Dataset is no longer raw
- [ ] Harness can produce baseline and treatment outputs with deterministic prompts at `temperature=0`

## Day 1 Afternoon and Evening

### Goal

Finish the grading pipeline and prove the benchmark works end to end on a few tasks.

### Requirements

- [ ] Harness is writing clean results
- [ ] E2B access works
- [ ] Judge model access works

### Codex Owns

- [ ] Implement the E2B sandbox grader
- [ ] Implement the error taxonomy
- [ ] Implement Claude-as-judge flow
- [ ] Implement composite scoring
- [ ] Implement result aggregation primitives

### You Own

- [ ] Approve extra spend if debugging requires a few additional runs
- [ ] Help if an account-level sandbox or billing issue appears

### Done When

- [ ] A `5-task` smoke test runs end to end
- [ ] Execution errors are classified correctly
- [ ] Judge output is parsed reliably

## Night 1

### Goal

Run the hard-gated pilot, not an ambiguous small sample.

### Requirements

- [ ] Smoke test passed
- [ ] Pipeline is stable enough to trust

### Codex Owns

- [ ] Select the exact `30-task` pilot set
- [ ] Run the pilot for Claude and GPT-4o in parallel
- [ ] Save results to separate directories keyed by model
- [ ] Ensure both model pilot datasets are ready before Day 2 Morning

### You Own

- [ ] Stay reachable for quota or billing issues

### Done When

- [ ] Pilot results exist for all `30 tasks` for Claude
- [ ] Pilot results exist for all `30 tasks` for GPT-4o
- [ ] Logging is sufficient to diagnose failures without blind reruns

## Day 2 Morning

### Goal

Use the pilot as a quality gate and stabilize the benchmark before the full run.

### Requirements

- [ ] Pilot output is complete and inspectable for both models

### Codex Owns

- [ ] Analyze pilot failures
- [ ] Separate harness bugs from weak tasks from genuine model failures
- [ ] Tighten retries and timeouts
- [ ] Fix sandbox install issues
- [ ] Freeze the scoring logic

### You Own

- [ ] Make final calls on whether to cut weak tasks or libraries instead of forcing them through

### Done When

- [ ] System is trustworthy
- [ ] System is reproducible
- [ ] Full dataset can run without major unknowns

## Day 2 Afternoon and Evening

### Goal

Freeze the dataset, launch the full benchmark run, and build the public artifact in parallel.

### Requirements

- [ ] Pilot is clean
- [ ] Dataset is strong enough to stand behind
- [ ] Budgets are acceptable

### Codex Owns

- [ ] Finalize the launch dataset
- [ ] Kick off the full eval
- [ ] Build the dashboard shell
- [ ] Wire `scores.json`
- [ ] Draft `README.md`
- [ ] Draft `CONTRIBUTING.md`
- [ ] Draft methodology copy

### You Own

- [ ] Approve the final dataset size if it lands below the stretch target
- [ ] Monitor real-world quota or billing constraints

### Done When

- [ ] Full run is underway or complete
- [ ] Dashboard and docs are mostly implemented instead of waiting on the run to finish

## Night 2

### Goal

Finish the full run and rerun only targeted failures.

### Requirements

- [ ] Aggregation and rerun tooling exist

### Codex Owns

- [ ] Run the full dataset through GPT-4o in parallel with the Claude full run
- [ ] Perform selective reruns
- [ ] Aggregate scores
- [ ] Flag odd deltas that need manual review

### You Own

- [ ] Step in only if external rate limits hit

### Done When

- [ ] Full-run outputs exist for both models
- [ ] Only targeted reruns remain
- [ ] Suspicious deltas are identified for review

## Day 3 Morning

### Goal

Turn results into a credible launch artifact with a clean narrative.

### Requirements

- [ ] Final or near-final scores are available

### Codex Owns

- [ ] Finish dashboard pages
- [ ] Finish task drilldowns
- [ ] Finish the methodology page
- [ ] Produce leaderboard analysis
- [ ] Produce screenshots or GIF
- [ ] Draft the X launch thread
- [ ] Draft a Show HN post with:
- [ ] Title starting with `Show HN:`
- [ ] One short paragraph explaining what it is and why it was built
- [ ] No marketing language
- [ ] Link to the repo, not the site

### You Own

- [ ] Approve the messaging, especially if some libraries show weak or negative deltas

### Done When

- [ ] Site tells a coherent story
- [ ] Headline number is defensible
- [ ] Show HN post is drafted and ready to submit in the Day 4 `9-11am US Eastern` window

## Day 3 Afternoon

### Goal

Ship the complete public version, including the auto-update story.

### Requirements

- [ ] Repo is launch-ready
- [ ] Deploy target exists
- [ ] Docs are nearly final

### Codex Owns

- [ ] Implement the GitHub Actions auto-update workflow
- [ ] Implement release-detection logic
- [ ] Implement draft-task PR flow
- [ ] Do final README polish
- [ ] Set up licensing
- [ ] Set up deployment config

### You Own

- [ ] Connect domain, DNS, Vercel, and GitHub settings where account ownership is required
- [ ] Enable required secrets in GitHub and Vercel

### Done When

- [ ] Site is live
- [ ] Repo is public-ready
- [ ] Weekly auto-update workflow is enabled

## Day 3 Evening

### Goal

Final QA and launch prep.

### Requirements

- [ ] Live site
- [ ] Public repo
- [ ] Screenshots ready
- [ ] Thread drafted

### Codex Owns

- [ ] Final copy edit
- [ ] Reproducibility check
- [ ] Short launch checklist

### You Own

- [ ] Post publicly
- [ ] Reply to people
- [ ] Follow up with Arlan if needed

### Done When

- [ ] Everything is launch-ready
- [ ] If following the PRD exactly, the thread is queued for the next morning in the `9-11am SF` window rather than posted late at night

## Day 4 Morning

### Goal

Publish distribution posts in the right windows.

### You Own

- [ ] Post the X thread in the `9-11am SF` window
- [ ] Submit the Show HN post in the `9-11am US Eastern` window

## Ownership Summary

### Codex Can Own

- [ ] Repo setup
- [ ] Dataset tooling
- [ ] Eval harness
- [ ] Direct Nia API integration
- [ ] Grading pipeline
- [ ] Dashboard
- [ ] Docs
- [ ] Auto-update workflow
- [ ] Launch materials

### You Own

- [ ] API keys
- [ ] Account setup
- [ ] Pre-run email to Arlan
- [ ] Domain and deployment ownership
- [ ] Final credibility calls on questionable tasks
- [ ] Public launch execution
