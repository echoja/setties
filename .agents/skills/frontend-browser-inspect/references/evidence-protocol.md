# Browser evidence protocol

Return one record per observation:

```json
{
  "observation_id": "checkout-form:error-spacing",
  "route": "/checkout",
  "component": "checkout-form",
  "semantic_state": ["submission:error", "validation:valid"],
  "selector": "[data-ui-component='checkout-form']",
  "role": "form",
  "accessible_name": "Checkout",
  "box": { "x": 120, "y": 80, "width": 640, "height": 420 },
  "computed": { "display": "grid", "gap": "4px", "overflowX": "visible" },
  "snapshot": null,
  "screenshot": ".ui-quality/evidence/.../checkout-form.png",
  "console": [],
  "requests": [],
  "observed_at": "2026-07-12T00:00:00Z"
}
```

Facts must be reproducible and scoped. Do not add severity, policy interpretation, or a proposed fix.

## Semantic state parsing

Treat `data-ui-state` as a space-separated list of `dimension:value` tokens. Each component owns only its state dimensions; do not flatten descendant state into the parent.

Allowed production diagnostics are bounded semantic values. If an attribute appears to contain a credential, private payload, personal data, or cross-tenant data, stop recording its value and report a security concern without copying the secret.

## Runtime inventory

Prefer a single page evaluation that returns compact JSON:

```js
async page => page.locator('[data-ui-component][data-ui-state]').evaluateAll(elements =>
  elements.map(element => {
    const box = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return {
      component: element.getAttribute('data-ui-component'),
      state: element.getAttribute('data-ui-state'),
      tag: element.tagName.toLowerCase(),
      box: { x: box.x, y: box.y, width: box.width, height: box.height },
      computed: {
        display: style.display,
        gap: style.gap,
        overflowX: style.overflowX,
        overflowY: style.overflowY,
      },
    };
  })
)
```

Use a targeted follow-up evaluation for additional properties. Avoid dumping entire stylesheets or HTML documents into context.
