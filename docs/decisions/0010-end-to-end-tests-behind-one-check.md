# Run the end-to-end tests only for the changes they test, behind one required check

- Status: accepted
- Date: 2026-10-13

## Context

The Docker end-to-end tests take about 20 minutes, mostly for the browser test of the cards, while every other check of a pull request is done in about 7. Over two weeks they were the last required check in 94 of 102 pull requests and used two thirds of the runner minutes, and more than half of the pull requests changed nothing they test: the documentation, workflows, the blueprint, the screenshot bot and tool updates. `main` required the three job names of their matrix, and a matrix that a condition or a path filter skips reports none of its names, so a plain filter would leave a pull request waiting for them forever. A skipped job, on the other hand, counts as passed.

## Options

1. Keep running every test for every pull request: safe, but every pull request waits 20 minutes or more, and the 20 jobs that the account runs at once fill up.
2. A path filter on the workflow and no required end-to-end check: fast, but a broken test could reach `main`.
3. A first job that asks the API which files a pull request changes, test jobs that run only when one of them is something the tests run or mount, and one gate job, `e2e`, that always runs and is the only required check.
4. An action of a third party that lists the changed files: one more dependency with access to the token of the workflow, for what one call of `gh api` does.

## Decision

Option 3. The gate passes when every test job passed, or when the first job found nothing for them to test, and fails when a test job failed, was cancelled or was skipped although it had to run. When in doubt, the tests run: when the API fails, or a pull request changes more files than the API lists. Every push to `main`, every night and every manual run tests everything, the nightly run also against the next Home Assistant.

## Consequences

A pull request that changes only the documentation or other workflows gets `e2e` within about a minute. The required check keeps its name when the matrix changes, so a new oldest Home Assistant or more jobs, such as shards of the browser test, change no ruleset. The list of what the tests use must keep up with the tests: `tests/test_consistency.py` fails when a compose file mounts, or the browser test reads, a file of the repository that the list misses, and a new job of the workflow must join the `needs` of the gate, which `tests/test_e2e_workflow.py` checks. A change outside the list that still breaks the tests shows on `main` or in the night, not in its pull request.
