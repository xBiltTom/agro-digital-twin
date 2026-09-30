import type { PlaybackResolution } from "../types/playback";
import type { SimulationAvailability } from "../types/playback-availability";

export type FirstCropNavigation =
  | { status: "READY"; date: string }
  | { status: "SELECT_DAILY" }
  | { status: "UNAVAILABLE" };

/** Prefer daily playback when that's where dated crop states are actually stored. */
export function preferredPlaybackResolution(availability: SimulationAvailability | null): PlaybackResolution | undefined {
  if (!availability) return undefined;
  const available = availability.resolutions.filter((item) => item.artifact_status === "AVAILABLE");
  return available.find((item) => item.resolution === "DAILY" && (item.fspm_trajectory_available || item.plant_samples_available))?.resolution
    ?? available.find((item) => item.resolution === "DAILY")?.resolution
    ?? available.find((item) => item.fspm_trajectory_available || item.plant_samples_available)?.resolution
    ?? available[0]?.resolution;
}

/** Returns only an indexed, representable date from an intact playback artifact. */
export function firstCropNavigation(
  availability: SimulationAvailability | null,
  resolution: PlaybackResolution | undefined,
): FirstCropNavigation {
  if (!availability || !resolution) return { status: "UNAVAILABLE" };
  const selected = availability.resolutions.find((item) => item.resolution === resolution);
  if (selected?.artifact_status === "AVAILABLE" && selected.first_representable_field) {
    return { status: "READY", date: selected.first_representable_field };
  }
  const daily = availability.resolutions.find((item) => item.resolution === "DAILY");
  if (resolution !== "DAILY" && daily?.artifact_status === "AVAILABLE" && daily.first_representable_field) {
    return { status: "SELECT_DAILY" };
  }
  return { status: "UNAVAILABLE" };
}
