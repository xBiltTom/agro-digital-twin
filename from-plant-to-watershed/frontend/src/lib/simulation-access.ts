import type { User } from "../types/auth";
import type { SimulationRun } from "../types/simulation";

/** Playback is owner scoped, with SUPERADMIN access to all runs. */
export function accessibleSimulations(runs: SimulationRun[], user: User): SimulationRun[] {
  return user.roles.some((role) => role.name === "SUPERADMIN")
    ? runs : runs.filter((run) => run.user_id === user.id);
}
