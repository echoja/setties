/** @ui-inspectable */
export function AccountPanel() {
  return (
    <section {...uiStateProps("account-panel", { disclosure: "open" })}>
      Account
    </section>
  );
}
