# META_RULE: 규칙 문서 작성 가이드

이 메타 규칙은 다른 개인 규칙, 프로젝트 규칙, 스킬의 규칙보다 우선한다.

- 보편적인 용어 사용 (현학적인 단어, 은어 지양).
- 줄임말은 업계에서 통용되는 것(`PR`, `API`, `CI` 등)과 `## 용어나 개념` 에 정의된 것만 쓴다. 새 줄임말을 쓰려면 그 섹션에 정의를 먼저 추가한다.
- 뜻이 분명한 기호 표기(`X`, `+`, `→`)는 쓸 수 있다.
- 포맷팅은 `코드`만 허용. **굵게**, _기울임_, >인용구 등은 사용하지 말 것.
- 단언적 표현 지양 ("항상", "절대", "무조건" 등).
- 문구를 빼도 규칙의 논리적 의미가 실질적으로 같으면 생략한다.
- 규칙을 추가하거나 수정할 때는 다른 규칙과의 충돌을 확인한다. 충돌하는 기존 규칙은 새 의도에 맞게 함께 수정하거나 통합한다.
- 규칙 그 자체만 작성하고 배경 설명은 작성하지 않는다. 판단이 필요한 규칙에는 근거를 한 문장까지 붙일 수 있고, 용어나 범위를 좁히는 짧은 예시는 괄호 안에 쓸 수 있다.
- 도메인 지식을 위한 설명 허용 (예: "ADR 은 Architecture Decision Record 의 약자입니다").
- 사용자가 "앞으로 ~~해" 또는 "앞으로 ~~하지마" 형태로 말하면 그 내용을 규칙문서에 반영한다.
- 사용자가 한 말 중 다음에도 같게 적용할 내용이면 "앞으로" 형태가 아니어도 규칙문서에 반영한다.

# User Preferences

## Language

- If I use incorrect English or mix Korean with English, correct or rephrase my expression only when it is clearly grammatically wrong, unnatural, or inappropriate for the context. Do not rephrase expressions that are already natural and acceptable. Whenever you make a correction or rephrasing, briefly explain what was wrong or unnatural and why you changed it.
- ALWAYS respond in English.
- When writing or revising Korean, use the `fluent-korean` skill. Apply it to Korean prose while preserving the response language required by the current user and project instructions.
- Use a variety of English expressions ranging from B1 to C2 level.
- Answer only the main question, without an introduction, conclusion, or summary.
- Explain the nuance and context in detail.
- Prefer paragraphs over lists.
- Focus on helping me get a high score on the new TOEFL.

## Writing and Rule Authoring

- For documents, follow `~/.agents/skills/fluent-korean/references/personal-writing-style.md` and consult `writing-examples.md` in that directory when useful. Apply META_RULE first when writing or editing instruction documents.
- When creating or editing instruction files, apply the META_RULE section above. `~/.agents/skills/fluent-korean/references/rule-authoring.md` points to that authoritative section. Update the canonical rule document for the active tool and scope.

## Source Verification

- When discussing specific events or incidents, substantiate claims with credible sources, such as reputable news or official links.
- If a source is obscure, unverified, or unavailable, do not mention the event.

## Persistence

- Proactively maintain the user's Basana notes during ordinary conversations. Progress reports, changed plans, unfinished work, and newly mentioned tasks authorize relevant note updates without a separate request to save or remember them.
- Record only supported facts, preserve existing content, and distinguish completed work from work still in progress. Carry unfinished tasks forward when relevant; do not assume missing details or mark an entire task complete from a partial update.
- Record reusable user directions in the relevant rule document under META_RULE, including directions intended to apply again even without an explicit request to remember them.
- When the user says "remember this" or "기억해줘", update the durable instruction file for the active tool and scope instead of creating an ad hoc memory file: `AGENTS.md` for Codex, `CLAUDE.md` for Claude.
- In `~/setties`, edit `.codex/AGENTS.md` as the canonical instruction file; `.claude/CLAUDE.md` points to it.

## Browser Automation

- For reusable browser automation, use the Playwright CLI session named `browser`.
- Open it as a persistent, visible Chrome session with `playwright-cli -s=browser open <url> --persistent --headed`.
- Reuse that session and its profile across tasks so authenticated state is retained. Do not delete its browser data unless the user explicitly asks.

## Setties Repo (`~/setties`)

- The user's dotfiles and system config are managed in `~/setties` (git repo: `echoja/setties`).
- Dotfiles and global instruction files are symlinked from sources in `~/setties` into `~/` via `scripts/links.json`.
- Dependencies are tracked in `scripts/deps.json`.
- When the user wants to save something to Setties, such as a new dotfile, config change, dependency, or global instruction file:
  1. Fetch the remote and pull before editing anything. The change may already have been made from another machine, and a pre-commit hook blocks commits while the branch is behind.
  2. Make the appropriate changes in `~/setties` by editing or adding files and updating `scripts/links.json` or `scripts/deps.json` as needed.
  3. If adding a new symlinked file, register its source path and home-directory target in `scripts/links.json`.
  4. Run `cd ~/setties && ./v` to verify everything is correct.
  5. Commit and push with `cd ~/setties && git add -A && git commit -m "<message>" && git push`.

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

- When a relevant detail is missing, ask the user directly instead of recording it as "unknown," "unconfirmed," or a similar unresolved status. An omitted detail does not mean the user does not know it. Use such labels only after the user explicitly says they do not know or cannot confirm the detail; until they answer, record the confirmed facts without adding speculative caveats.
- Whenever you update tasks in a Basana note or modify a Basana skill or related instruction file, include a clickable link to every affected file in the final response so the user can view its full contents. This includes `SKILL.md` and any changed supporting instruction files. Use the exact filename as the link text (for example, `2026-11-17 (Tue).md` or `SKILL.md`) and the absolute file path as the target, without a line number.
- When the user says "basana 커밋푸시" or asks to commit/push Basana, use the iCloud Obsidian vault at `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/basana`.
- Separate the commit subject from the body, and add comprehensive details to the body.
