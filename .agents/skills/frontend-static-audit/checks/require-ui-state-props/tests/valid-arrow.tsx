/** @ui-inspectable */
export const PaymentSelector = () => (
  <section {...uiStateProps("payment-selector", { selection: "card" })} />
);
