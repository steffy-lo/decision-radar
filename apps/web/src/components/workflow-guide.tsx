import Link from "next/link";

const steps = [
  { slug: "connections", title: "Connect files", description: "Choose a Drive folder and refresh its files." },
  { slug: "decisions", title: "Confirm a decision", description: "Record the original plan and the deadline it depends on." },
  { slug: "sources", title: "Extract updates", description: "Turn new source text into verified facts." },
  { slug: "reviews", title: "Check for conflicts", description: "Compare the facts, then review any challenged decision." },
] as const;

export function WorkflowGuide({ projectId, current }: { projectId: string; current: typeof steps[number]["slug"] }) {
  return <nav className="workflow-guide" aria-label="How to check a decision">
    <div className="workflow-guide__heading"><strong>From documents to a decision check</strong><span>Follow these steps in order</span></div>
    <ol>{steps.map((step, index) => <li key={step.slug}>
      <Link href={`/projects/${encodeURIComponent(projectId)}/${step.slug}`} aria-current={current === step.slug ? "step" : undefined}>
        <span className="workflow-guide__number" aria-hidden="true">{index + 1}</span>
        <span><strong>{step.title}</strong><small>{step.description}</small></span>
      </Link>
    </li>)}</ol>
  </nav>;
}
