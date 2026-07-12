# Conservative baseline principles

These are heuristics, not aesthetic laws. Apply them only with evidence and user/maintenance impact.

## Proximity and grouping

- Related elements should be measurably grouped more tightly than unrelated sections.
- Adjacent interactive targets must not overlap or become difficult to distinguish or operate.
- Repeated equivalent groups should use consistent realized spacing unless policy documents a reason.

Do not impose a universal pixel scale. Prefer project tokens, repeated intentional patterns, touch geometry, and actual collision evidence.

## Hierarchy and scanability

- The primary task and current state should remain discoverable from structure, semantics, and visual emphasis.
- Heading/landmark order and DOM order should support the intended reading order.
- Repeated elements with different importance should not become indistinguishable when that slows or misdirects task completion.

Do not demand dramatic typography or a particular visual style.

## Interaction feedback

- User actions should expose meaningful pending, success, error, disabled, selected, expanded, or empty states when those states exist.
- Focus and keyboard state must remain perceivable and operable.
- Semantic `data-ui-state` diagnostics may explain the rendered state but never replace native HTML or ARIA.

## Responsive behavior

- Content should reflow without accidental clipping, overlap, unreachable controls, or unreadable line lengths.
- Components should adapt to their actual content/container pressure instead of accumulating arbitrary device breakpoints.
- Long copy, zoom, localization, and narrow widths are evidence probes, not style preferences.

## Consistency and maintainability

- Equivalent semantics should map to canonical tokens and component behavior.
- Repeated one-off literals or component variants may indicate a missing system rule.
- A systemic root cause should suppress dependent findings until resolved.

## Excluded taste

Do not enforce preferred fonts, palettes, border radii, shadows, card usage, asymmetry, animation character, novelty, or trend avoidance unless humans put them in policy.
