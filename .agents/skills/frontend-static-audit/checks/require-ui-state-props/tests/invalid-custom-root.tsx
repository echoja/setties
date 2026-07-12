/** @ui-inspectable */
export function ProfilePanel() {
  return <Panel {...uiStateProps("profile-panel", { disclosure: "open" })} />;
}
