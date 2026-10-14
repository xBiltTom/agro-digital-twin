import type { User } from "../types/auth";
import type { SimulationRun } from "../types/simulation";

/** Playback is owner scoped, with SUPERADMIN access to all runs. */
export function accessibleSimulations(runs: SimulationRun[], user: User): SimulationRun[] {
  return user.roles.some((role) => role.name === "SUPERADMIN")
    ? runs : runs.filter((run) => run.user_id === user.id);
}

/** Prefer the full 2019 plant-to-watershed demo when it is registered and accessible. */
export function preferredTwinSimulation(runs: SimulationRun[]): SimulationRun | null {
  const completed = runs.filter((run) => run.status === "COMPLETED");
  return completed.find((run) => run.id === "phase234-sf-2019-v2")
    ?? completed.find((run) => run.name.startsWith("South Fork · reproducción B"))
    ?? completed.find((run) => run.id === "sf-test-v1-b-2025")
    ?? runs[0]
    ?? null;
}

/** Fetch every owner-scoped API page without changing the server's pagination contract. */
export async function collectSimulationPages(
  fetchPage: (skip: number, limit: number) => Promise<SimulationRun[]>, pageSize = 100,
): Promise<SimulationRun[]> {
  const runs: SimulationRun[] = [];
  for (let skip = 0; ; skip += pageSize) {
    const page = await fetchPage(skip, pageSize);
    runs.push(...page);
    if (page.length < pageSize) return runs;
  }
}
