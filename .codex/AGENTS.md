# User Preferences

## Language

- If I use incorrect English or mix Korean into my English, please correct it by suggesting a natural and accurate expression.
- Please respond in English at a B1-C2 level, using a variety of natural expressions.
- Skip the introduction, conclusion, and summary. Answer with only the main content.

## Source Verification

- When discussing specific events or incidents, substantiate claims with credible sources, such as reputable news or official links.
- If a source is obscure, unverified, or unavailable, do not mention the event.

## Persistence

- Do not proactively save persistent notes or memories.
- Only write persistent notes when the user explicitly asks to remember something.
- When the user says "remember this" or "기억해줘", update the durable instruction file for the active tool and scope instead of creating an ad hoc memory file: `AGENTS.md` for Codex, `CLAUDE.md` for Claude.
- In `~/setties`, edit `.codex/AGENTS.md` as the canonical instruction file; `.claude/CLAUDE.md` points to it.

## Setties Repo (`~/setties`)

- The user's dotfiles and system config are managed in `~/setties` (git repo: `echoja/setties`).
- Dotfiles and global instruction files are symlinked from sources in `~/setties` into `~/` via `scripts/links.json`.
- Dependencies are tracked in `scripts/deps.json`.
- When the user wants to save something to Setties, such as a new dotfile, config change, dependency, or global instruction file:
  1. Make the appropriate changes in `~/setties` by editing or adding files and updating `scripts/links.json` or `scripts/deps.json` as needed.
  2. If adding a new symlinked file, register its source path and home-directory target in `scripts/links.json`.
  3. Run `cd ~/setties && ./v` to verify everything is correct.
  4. Commit and push with `cd ~/setties && git add -A && git commit -m "<message>" && git push`.

## Basana Obsidian Vault

- When the user says "basana 커밋푸시" or asks to commit/push Basana, use the iCloud Obsidian vault at `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/basana`.
- Treat that phrase as a request to commit and push all pending Git changes in that vault, unless the user specifies a narrower scope. Check status, stage with `git add -A`, commit with a concise vault-note message, and push the current branch.
