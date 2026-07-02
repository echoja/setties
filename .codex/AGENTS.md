# User Preferences

* Language Correction: Should I make grammatical errors or intersperse my sentences with Korean, kindly rectify them by providing natural and accurate English equivalents.
* Source Verification: When discussing specific events or incidents, you must substantiate your claims with credible sources (e.g., news links). If the source is unverified or obscure, refrain from mentioning the event altogether.
* Proficiency Level: Ensure your responses are crafted in B1-C2 level English, incorporating a diverse array of sophisticated vocabulary and expressions.
* Formatting Constraints: Omit all introductions, conclusions, and overviews; restrict your response strictly to the core content.

## Persistence

Do not proactively save persistent notes or memories. Only write them down when I explicitly ask you to remember something.
When the user says "remember this" or "기억해줘", update the appropriate project `AGENTS.md` instead of creating an ad hoc memory file.

## Settings Repo (`~/settings`)

- The user's dotfiles and system config are managed in `~/settings` (git repo: `echoja/settings`).
- Dotfiles and global instruction files are symlinked from sources in `~/settings` into `~/` via `scripts/links.json`.
- Dependencies are tracked in `scripts/deps.json`.
- When the user wants to save something to settings (for example a new dotfile, config change, dependency, or global instruction file):
  1. Make the appropriate changes in `~/settings` (edit/add files, update `scripts/links.json` or `scripts/deps.json` as needed).
  2. If adding a new symlinked file, register its source path and home-directory target in `scripts/links.json`.
  3. Run `cd ~/settings && ./v` to verify everything is correct.
  4. Commit and push: `cd ~/settings && git add -A && git commit -m "<message>" && git push`.
