import fs from "node:fs";
import path from "node:path";

import type { AgentScoresFile } from "@/lib/agent-types";

const CANDIDATE_AGENT_SCORE_PATHS = [
  path.resolve(process.cwd(), "results/agent_scores.json"),
  path.resolve(process.cwd(), "../results/agent_scores.json"),
  path.resolve(process.cwd(), "../../results/agent_scores.json"),
];

export function loadAgentScores(): AgentScoresFile {
  const scoresPath = resolveAgentScoresPath();
  const file = fs.readFileSync(scoresPath, "utf8");
  return JSON.parse(file) as AgentScoresFile;
}

function resolveAgentScoresPath(): string {
  for (const candidate of CANDIDATE_AGENT_SCORE_PATHS) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error(
    `Could not locate results/agent_scores.json. Checked: ${CANDIDATE_AGENT_SCORE_PATHS.join(", ")}`,
  );
}
