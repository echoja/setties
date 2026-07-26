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

## Springfall Legacy Article Migration (`~/works/springfall-astro`)

- When migrating an `elvanov.com/<post-id>` article into Springfall, first search the current content tree and Git history for the post ID, title, and distinctive text to avoid duplicates.
- Treat the WordPress REST API as the source of truth. Fetch the post from `https://elvanov.com/wp-json/wp/v2/posts/<post-id>` and use its title, publication date, modified date, headings, body, emphasis, code, lists, quotations, links, and captions. Use the category and media endpoints when needed.
- Preserve the original article wording. Only make changes required for valid, idiomatic MDX, such as converting HTML to Markdown, selecting fenced-code languages, and escaping literal angle brackets. Add the required summary and map legacy categories to the categories allowed by the current schema.
- Store the article at `src/content/articles/YYYY-MM/<english-slug>/ko.mdx`. Article routes must use `/ko/article/YYYY-MM/<english-slug>/`.
- Inventory every inline and featured image. Resolve media IDs through `https://elvanov.com/wp-json/wp/v2/media/<media-id>` and download the original `source_url`, not a resized `i0.wp.com` URL. Store images in the article's `assets/` directory, verify their type and original dimensions, and give them meaningful filenames.
- Import local images through ESM and render them with `ArticleImage` using `img={...}`, the original caption, and a descriptive `alt`. Do not leave migrated images hosted on WordPress.
- After migration, compare the source and rendered page for title, dates, sections, body, emphasis, code blocks, lists, links, captions, image count, and image dimensions. Run `pnpm validate` and `pnpm build`, then check that the localized route returns HTTP 200. Restart the Astro dev server if a newly added content directory causes a stale `UnknownContentCollectionError`.
- Commit only the migration files. Preserve unrelated working-tree changes, and do not push or deploy Springfall unless the user explicitly asks.

## Basana Obsidian Vault

- When the user says "basana 커밋푸시" or asks to commit/push Basana, use the iCloud Obsidian vault at `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/basana`.
- Separate the commit subject from the body, and add comprehensive details to the body.
