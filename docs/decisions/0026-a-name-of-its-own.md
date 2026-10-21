---
description: "Why the integration is now HomeDarts for Autodarts, with the domain homedarts and an icon of its own: Autodarts asked for its name and logo to go."
---

# A name of its own: HomeDarts for Autodarts, with the domain homedarts

- Status: accepted
- Date: 2026-10-21

## Context

Up to version 1.18 the integration was called Autodarts, had the domain `autodarts` and showed the logo of Autodarts as its icon, with notes that it is an unofficial community project. On 2026-10-21 Autodarts asked the project to remove its protected logo completely and to stop using the name Autodarts on its own: the name and the logo make users think of an offer of Autodarts, whatever the documentation says. A purely descriptive addition is allowed, such as "[name] for Autodarts".

The integration is young: it is in the HACS default catalog since 2026-10-20, and few people use it. Its domain is in the names of its actions, such as `autodarts.start_game`, of its cards, its dashboard strategy, its folders and its stores, and in every automation and dashboard of its users.

People look for it by the word "autodarts": in HACS, which searches the name, the description, the name of the repository and its topics; in the dialog *Add integration* of Home Assistant, which searches only the name and the domain; on GitHub, which ranks a match in the name of the repository first; and with search engines.

## Options

1. Change only what users see, the name and the icon, and keep the domain `autodarts`: nothing breaks, but every action, card and folder keeps the name that Autodarts asked to give up, for good.
2. Change the name, the icon and the domain now, while few people use the integration, and take over their boards with everything that they have.
3. A name without Autodarts and nothing more: search for "autodarts" would no longer find it in the dialog of Home Assistant.

## Decision

Option 2, with the name **HomeDarts for Autodarts**, the pattern that Autodarts allows, and **HomeDarts** for short. "HomeDarts" says what the integration is, darts at home in Home Assistant, with an Autodarts board, a Granboard or any dartboard by hand; no trade mark of that name is registered.

- The domain is `homedarts`, and so are the names of its actions, cards, strategy, folders and stores.
- The full name is the name of the integration in Home Assistant and HACS, of the website and the repository, `Dennis-Otto/homedarts-for-autodarts`, so that a search for "autodarts" still finds it everywhere; the repository keeps the topic `autodarts`.
- The icon is a house with a dartboard and a dart in its bull, the project's own and under its MIT license.
- What names the product of Autodarts keeps its name: an Autodarts board, the Board Manager, the manufacturer of the device, the entity IDs that come from the device name "Autodarts Board", "a dartboard without Autodarts".
- A board set up under the old name is taken over by HomeDarts, with its settings, its entities and their IDs, its stores, its media and its cards in the dashboards.

## Consequences

- The release is 2.0.0. HACS installs the integration into `custom_components/homedarts`, beside the old folder, which the takeover removes.
- Automations, scripts and dashboards in YAML that use the old actions or cards need the new names; a repair lists them, and the page [From Autodarts to HomeDarts](../new-name.md) explains the switch.
- The website moves to `https://dennis-otto.github.io/homedarts-for-autodarts/`; GitHub forwards the repository, and the website at the root of the address forwards the old pages.
- The entry in the HACS default catalog, the project at bestpractices.dev and the list of projects of the root website follow the new name of the repository.
