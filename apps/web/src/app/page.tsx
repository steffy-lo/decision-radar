import Link from "next/link";

export default function Home() {
  return (
    <main className="welcome-page">
      <div className="welcome-page__orb welcome-page__orb--one" aria-hidden="true" />
      <div className="welcome-page__orb welcome-page__orb--two" aria-hidden="true" />
      <div className="welcome-page__content">
        <div className="welcome-page__brand"><span className="brand__mark" aria-hidden="true"><span /></span> Decision<span>Radar</span></div>
        <span className="welcome-page__eyebrow">DECISION INTELLIGENCE FOR TEAMS</span>
        <h1>Keep every decision <em>in context.</em></h1>
        <p>Connect the evidence behind project decisions, catch changes that matter, and see their impact before your team moves forward.</p>
        <Link className="button button--primary button--large" href="/demo">Try connected demo <span aria-hidden="true">→</span></Link>
        <div className="welcome-page__note">No password needed · real Drive files with sample data</div>
        <Link className="text-link" href="/projects/proj_demo_2026/decisions">Explore the fixed walkthrough →</Link>
      </div>
      <div className="welcome-page__visual" aria-hidden="true">
        <div className="orbit orbit--outer" /><div className="orbit orbit--middle" /><div className="orbit orbit--inner" />
        <span className="orbit__node orbit__node--one" /><span className="orbit__node orbit__node--two" /><span className="orbit__node orbit__node--three" />
        <div className="orbit__center">DR</div>
      </div>
    </main>
  );
}
