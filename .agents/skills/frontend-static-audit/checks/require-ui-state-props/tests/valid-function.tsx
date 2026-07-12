/** @ui-inspectable */
export function CheckoutForm() {
  return <form {...uiStateProps("checkout-form", { submission: "idle" })} />;
}
