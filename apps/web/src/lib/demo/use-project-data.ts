"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { parseDemoFixture, type DemoFixture } from "@/lib/domain/models";

export const DEMO_PROJECT_ID = "proj_demo_2026";
export const isDemoProject = (projectId: string) => projectId === DEMO_PROJECT_ID;

type ProjectDataState = {
  projectId: string;
  status: "loading" | "ready" | "error";
  data: DemoFixture | null;
  error: string | null;
};

const loading = (projectId: string): ProjectDataState => ({
  projectId, status: "loading", data: null, error: null,
});

function projectDataUrl(projectId: string, scenario: string | null): string {
  const base = `/api/v1/projects/${encodeURIComponent(projectId)}`;
  if (!isDemoProject(projectId)) return `${base}/workspace`;
  return `${base}/fixture${scenario && ["access-unavailable", "evidence-unclear", "no-detected-issue"].includes(scenario) ? `?scenario=${scenario}` : ""}`;
}

export function useProjectData(projectId: string) {
  const scenario = useSearchParams().get("scenario");
  const [state, setState] = useState<ProjectDataState>(() => loading(projectId));
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetch(projectDataUrl(projectId, scenario), { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(isDemoProject(projectId)
            ? `Could not load project data (${response.status}).`
            : "Live project data is not connected yet.");
        }
        return response.json();
      })
      .then((value: unknown) => {
        if (!controller.signal.aborted) {
          setState({ projectId, status: "ready", data: parseDemoFixture(value), error: null });
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ projectId, status: "error", data: null, error: error instanceof Error ? error.message : "Could not load project data." });
        }
      });
    return () => controller.abort();
  }, [projectId, scenario, attempt]);

  const retry = useCallback(() => {
    setState(loading(projectId));
    setAttempt((value) => value + 1);
  }, [projectId]);

  const current = state.projectId === projectId ? state : loading(projectId);
  return { status: current.status, data: current.data, error: current.error, retry };
}
