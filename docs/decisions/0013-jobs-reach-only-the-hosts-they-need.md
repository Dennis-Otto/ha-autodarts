---
description: "Why the jobs of the workflows of the project may reach only the hosts they need, and the Home Assistant under test none at all."
---

# Let the jobs of the project's workflows reach only the hosts they need, and the Home Assistant under test none

- Status: accepted
- Date: 2026-10-14

## Context

Every job of the workflows started Harden-Runner with `egress-policy: audit` and sudo allowed. Audit mode records where a job connects, but stops nothing: a compromised action, npm or Python package, or a test of a pull request could send the token of a job, or the key of the release app in the screenshot bot, to any host, and the record would show it afterwards. The project's own jobs reach very few hosts, as the records of their runs show: the translation bot, the comment of the visual check and the pull request of the screenshot bot only GitHub, the end-to-end tests and the images the registries of their images and the indexes of their packages. The Home Assistant under test also called the internet: its onboarding sets up Radio Browser, which looks up radio stations on `all.api.radio-browser.info` as soon as it starts, in every scenario, browser and image job, so the tests depended on a service outside, and the images showed a Radio Browser that no user of the integration needs.

## Options

1. Keep audit mode and read the records now and then: no risk of a blocked step, and no protection.
2. Block every host that a job doesn't list, in the bots only, which hold write tokens: the most valuable step, but the tests and the images run the code of pull requests with the same Actions and packages.
3. Block in every job of the project's own workflows, with the hosts that their runs reached, and take away sudo and Docker where no step starts a container, so that no step can lift the block.
4. For the Home Assistant under test, remove the entry of Radio Browser after onboarding: Home Assistant sets it up within a second, so its first request leaves before any test could remove it.
5. Put a stand-in for Radio Browser into the container as a custom integration, whose config flow turns down the offer of onboarding: Home Assistant prefers a custom integration to its built-in one of the same name, and the stand-in reaches nothing.

## Decision

Options 3 and 5. Harden-Runner blocks every host that the steps of a job don't need in the end-to-end tests, the visual check, its comment, the screenshot bot and the translation bot; each job names its hosts with port 443 and says in a comment what they are for. The jobs that may write reach GitHub alone, and every job without containers runs without sudo and Docker. `tests/e2e/offline/radio_browser` takes the place of Radio Browser in every Home Assistant of the tests, the demo and the images, and the scenario checks that no entry of it exists. Only the demo of the images still loads the icons of Home Assistant's built-in integrations from its CDN, `brands.home-assistant.io`, because the integrations page in the images shows them. The workflows that the blueprint keeps follow its own rules.

## Consequences

A step that needs a new host fails, and the log of the job's last step, the post step of Harden-Runner, names the host as `domain not allowed: <host>`, until the host joins the list of its job and `tests/test_workflow_network.py`, which fails for an unknown job, an unexpected host, a job in audit mode, a job without containers that keeps sudo, and a job that may write and reaches more than GitHub. A new Home Assistant or Playwright image from another registry, or a new tool of the images, therefore comes with its host. Harden-Runner filters the runner and Docker's default network by address; the containers on the networks of Compose are held back by its DNS, which resolves only the hosts of the job. The integrations page in the images no longer shows Radio Browser, and the end-to-end tests pass without the internet once their images and packages are there.
