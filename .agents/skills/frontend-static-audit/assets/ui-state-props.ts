export type UIStateValue = string | boolean | null | undefined;

export type UIState = Readonly<Record<string, UIStateValue>>;

export type UIStateAttributes = Readonly<{
  "data-ui-component": string;
  "data-ui-state": string;
}>;

const semanticToken = /^[a-z][a-z0-9-]*$/;

function assertSemanticToken(value: string, label: string): void {
  if (!semanticToken.test(value)) {
    throw new Error(`${label} must be a lowercase semantic token: ${value}`);
  }
}

/**
 * Expose bounded, semantic component state as production-safe DOM diagnostics.
 * Never pass secrets, private payloads, user identifiers, or authorization data.
 */
export function uiStateProps(
  component: string,
  state: UIState,
): UIStateAttributes {
  assertSemanticToken(component, "component");

  const serialized = Object.entries(state)
    .filter((entry): entry is [string, string | boolean] => {
      return entry[1] !== null && entry[1] !== undefined;
    })
    .map(([dimension, value]) => {
      assertSemanticToken(dimension, "state dimension");
      const semanticValue = String(value);
      assertSemanticToken(semanticValue, `state value for ${dimension}`);
      return `${dimension}:${semanticValue}`;
    })
    .join(" ");

  if (!serialized) {
    throw new Error("uiStateProps requires at least one semantic state dimension");
  }

  return {
    "data-ui-component": component,
    "data-ui-state": serialized,
  };
}
