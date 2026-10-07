## Your task: the first analysis of issue #{issue}

The context files:

- `{context}/issue.md`: the issue with its comments. Read it completely first.
- `{context}/issues.jsonl`: every other issue of the repository, one JSON object per line with number, title, state, state_reason, labels, dates and an excerpt. Search it with Grep.
- `{context}/discussions.jsonl`: the GitHub Discussions, in the same form.
- `{context}/labels.md`: the labels you choose from.

The version on main is {version}; the latest release is {release}.

1. **Understand the issue:** what the reporter does, expects and observes; the versions of the integration, Home Assistant and the Autodarts software on the board PC; the part of the integration concerned. The issue form's answers and choices are hints: the text is what counts when they disagree.
2. **Investigate in the repository.** Read the documentation of the topic (for German reporters also `docs/de/`), especially `docs/troubleshooting.md`, and check `CHANGELOG.md`: was it fixed or changed in a version newer than the reporter's? Then look at the code in `custom_components/autodarts/` or the blueprint involved. Find the most likely cause, or at least the part of the code involved. For a feature request: what exists today, whether `docs/roadmap.md` plans it, and what it would touch. For a question: the answer from the documentation. For a compatibility report or tester feedback: what it means for other players and which points are known issues.
3. **Search for duplicates and related issues.** Grep `issues.jsonl` and `discussions.jsonl` with several different sets of keywords, in English and German: error messages, entity and card names, game names, symptoms. Read the promising lines completely.
   - `duplicates`: only issues about the same problem or the same request, not just the same area. `"high"` only when you are sure that one fix or one decision settles both, and only for an open issue; otherwise `"medium"`. Leave it empty when there is none.
   - `related`: issues and discussions that help, each with the reason: a fix in a closed issue, a similar report, a discussion with an answer. Don't repeat the duplicates.
4. **Decide what's missing.** `missing_information` lists only what blocks progress and is not in the issue yet, each as a concrete request that says where to find it, for example "Which version of the Autodarts software runs on the board PC? The device page of the board in Home Assistant shows it." Ask for the diagnostics, log lines with debug logging or steps to reproduce only when this problem needs them. Leave it empty for feature requests, tester feedback and compatibility reports of working setups, and whenever the issue has what is needed.
5. **Choose the labels.** `kind` is the one kind that fits best. `areas` are the parts of the integration concerned, at most three, or none. `topics` only when accessibility or translations are central. `label_rationale` explains your choice in one sentence. Use the kind `"spam"` for advertising, nonsense and issues that have nothing to do with this integration; then keep all texts short.
6. **Write the answer.**
   - `summary`: two or three sentences that restate the issue precisely, so that the maintainer understands it without reading it.
   - `analysis`: what you found: the likely cause or the code involved, what the documentation says, whether a newer version changed it; for a feature request how it fits into what exists and the roadmap. At most about 250 words; no repetition of the summary.
   - `next_steps`: concrete things the reporter can do now, such as a workaround, an option or an update, or nothing. Don't repeat what `missing_information` asks for.
   - `references`: the files that matter most, at most six. `path` is relative to the repository root. Give `line` for code (the line that matters) or `anchor` for a heading of a Markdown file (GitHub's anchor, such as `no-realtime-updates`). Prefer the documentation in the reporter's language.
   - `sensitive_data`: true when the issue or a comment contains a token, a key, a password, a public IP address or similar personal data.
   - `security_report`: true when the issue reports a security vulnerability. Then keep `analysis` to one neutral sentence and leave `next_steps`, `missing_information`, `duplicates` and `related` empty.
