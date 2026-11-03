# ProofPay Agent 2 Integration Notes

## Non-disruptive integration

Agent 1 remains the existing scoping graph. Its approval and lock sequence is not replaced or reordered. The only Agent 1 behavior change in this build is that an unspecified payment provider is not treated as an unresolved scoping requirement.

Agent 2 is a separate LangGraph graph and FastAPI router. It is eligible to run only when:

- the project row has `status == PLAN_APPROVED`;
- a matching persisted `plan.approved` event exists for the current `plan_hash`;
- the submitted milestone ID belongs to the locked plan; and
- the submitting freelancer ID matches the project participant.

Agent 2 starts only after the freelancer submits evidence. It reads the approved milestone but never mutates the approved plan. Verification attempts are saved to `verification_submissions`, separately from the `projects` JSON record.

## Supported deterministic checks

- `url_returns_200`
- `url_contains_text`
- `github_pr_merged`
- `github_checks_passing` (GitHub combined commit status)
- `repo_file_exists`
- `file_type_size` (submitted metadata)
- `file_has_sections` (submitted text evidence)

`deliverable_check`, `manual_review`, and unsupported criterion types remain `review_required`. Agent 2 never marks them passed based only on an LLM response.

## Decision semantics

- `RESUBMISSION_REQUIRED`: a `must_pass` criterion failed.
- `CLIENT_REVIEW_REQUIRED`: human review is needed, evidence is missing, or the weighted score is below 90%.
- `RELEASE_PROPOSAL`: all criteria are objectively verified and weighted score is at least 90%. This is not a payment action.

The weighted score is deterministic. Gemini, when configured, may only produce a plain-language explanation of the already-computed result.

## API

- `POST /api/v1/verification/projects/{project_id}/milestones/{milestone_id}/submissions`
- `GET /api/v1/verification/projects/{project_id}/milestones/{milestone_id}/submissions`

The local API currently checks the supplied freelancer ID against the project record. Production deployment must replace this with authenticated identity/session authorization.
