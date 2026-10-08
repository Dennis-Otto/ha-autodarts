# Talk to the board through the local API of the Board Manager

- Status: accepted
- Date: 2026-09-26

## Context

An Autodarts board runs the Board Manager on a small PC next to the board. It offers a local HTTP and WebSocket API on the home network (Board Manager 1 and 2) with the state of the board, every dart and the camera streams. The Autodarts cloud has the matches and the profiles, but a third-party integration needs a client ID from Autodarts to use it, which Autodarts hasn't granted yet.

## Options

1. Wait for the cloud and build on it only.
2. Read the local API of the Board Manager, and add the cloud when a client ID exists.
3. Scrape the web app of Autodarts.

## Decision

Option 2. The integration talks to the Board Manager on the local network only: discovery, the events of every dart, the camera streams and the commands of the board. It keeps no cloud credentials. The link to the cloud stays hidden (`CLOUD_LINK_AVAILABLE = False`) until Autodarts grants a client ID; Autodarts was asked first and reviews the use of the local interface.

## Consequences

Everything works offline and without an Autodarts account, with Board Manager 1 and 2. Games and statistics that the cloud would hold run in Home Assistant itself ([0003](0003-games-and-statistics-in-home-assistant.md)). A change of the local API by Autodarts can break the integration; the end-to-end tests run against both Board Managers and a mock of them.
