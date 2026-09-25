import type { User } from "../types/auth";
import type { SimulationRun } from "../types/simulation";

/** Playback is owner scoped, with SUPERADMIN access to all runs. */
export function accessibleSimulations(runs: SimulationRun[], user: User): SimulationRun[] {
  return user.roles.some((role) => role.name === "SUPERADMIN")
    ? runs : runs.filter((run) => run.user_id === user.id);
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
