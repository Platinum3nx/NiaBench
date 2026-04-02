import fs from "node:fs";
import path from "node:path";

import type { ScoresFile } from "@/lib/types";

const CANDIDATE_SCORE_PATHS = [
  path.resolve(process.cwd(), "results/scores.json"),
  path.resolve(process.cwd(), "../results/scores.json"),
  path.resolve(process.cwd(), "../../results/scores.json"),
];

export function loadScores(): ScoresFile {
  const scoresPath = resolveScoresPath();
  const file = fs.readFileSync(scoresPath, "utf8");
  return JSON.parse(file) as ScoresFile;
}

function resolveScoresPath(): string {
  for (const candidate of CANDIDATE_SCORE_PATHS) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error(
    `Could not locate results/scores.json. Checked: ${CANDIDATE_SCORE_PATHS.join(", ")}`,
  );
}
