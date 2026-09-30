export default function Loading() {
  return (
    <div className="route-loading" aria-busy="true" aria-label="Loading workspace">
      <div className="route-loading__line" />
      <div className="route-loading__line route-loading__line--short" />
      <div className="route-loading__panel" />
    </div>
  );
}
