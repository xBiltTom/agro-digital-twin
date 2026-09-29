"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import { PlaybackClient, PLAYBACK_PAGE_SIZE } from "../lib/playback-client";
import { firstCropNavigation } from "../lib/playback-navigation";
import type { PlaybackPage, PlaybackResolution } from "../types/playback";
import type { SimulationAvailability } from "../types/playback-availability";

export function useTwinPlayback(simulationId: string | null) {
  const client = useMemo(() => new PlaybackClient((id, query, signal) => api.getPlayback(id, query, signal)), []);
  const [resolution, setResolution] = useState<PlaybackResolution | undefined>(undefined);
  const [index, setIndex] = useState(0);
  const [page, setPage] = useState<PlaybackPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [availability, setAvailability] = useState<SimulationAvailability | null>(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const requestNumber = useRef(0);
  const dateRequestNumber = useRef(0);
  const total = page?.total ?? 0;
  // A mutable client cache alone is invisible to React's render dependencies.
  // Read the stateful page first so the initial record appears when fetch resolves.
  const currentRecord = page && index >= page.offset && index < page.offset + page.records.length
    ? page.records[index - page.offset] : client.recordAt(index);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      if (controller.signal.aborted) return;
      setAvailability(null);
      setAvailabilityLoading(Boolean(simulationId));
    });
    if (simulationId) {
      api.getPlaybackAvailability(simulationId, undefined, controller.signal)
        .then((result) => { if (!controller.signal.aborted) setAvailability(result); })
        .catch(() => { if (!controller.signal.aborted) setAvailability(null); })
        .finally(() => { if (!controller.signal.aborted) setAvailabilityLoading(false); });
    }
    return () => controller.abort();
  }, [simulationId]);

  useEffect(() => {
    client.select(simulationId, resolution);
    const request = ++requestNumber.current;
    dateRequestNumber.current += 1;
    queueMicrotask(() => {
      if (request !== requestNumber.current) return;
      setIndex(0);
      setPage(null);
      setError(null);
      setPlaying(false);
      setLoading(Boolean(simulationId));
    });
    if (!simulationId) return;
    client.pageFor(0).then((result) => {
      if (request !== requestNumber.current) return;
      setPage(result);
      setLoading(false);
    }).catch((cause: unknown) => {
      if (request !== requestNumber.current) return;
      setError(cause instanceof Error ? cause.message : "No se pudo consultar la reproducción");
      setLoading(false);
    });
    return () => { requestNumber.current += 1; dateRequestNumber.current += 1; client.select(null); };
  }, [client, simulationId, resolution]);

  useEffect(() => {
    if (!simulationId || index === 0) return;
    const request = ++requestNumber.current;
    if (client.recordAt(index)) {
      const cached = client.loadedPage(index);
      if (cached) queueMicrotask(() => {
        if (request !== requestNumber.current) return;
        setPage(cached);
        setError(null);
        setLoading(false);
      });
    } else {
      queueMicrotask(() => { if (request === requestNumber.current) setLoading(true); });
      client.pageFor(index).then((result) => {
        if (request !== requestNumber.current) return;
        setPage(result);
        setError(null);
        setLoading(false);
      }).catch((cause: unknown) => {
        if (request !== requestNumber.current) return;
        setError(cause instanceof Error ? cause.message : "No se pudo cargar el periodo");
        setLoading(false);
      });
    }
    if (total > 0 && index % PLAYBACK_PAGE_SIZE >= PLAYBACK_PAGE_SIZE - 12 && index + 1 < total) {
      void client.pageFor(index + 12).catch(() => undefined);
    }
  }, [client, simulationId, index, total]);

  useEffect(() => {
    if (!playing || !page?.total || loading || !currentRecord || currentRecord.simulation_id !== simulationId) return;
    const timer = window.setInterval(() => setIndex((old) => old + 1 < page.total ? old + 1 : 0), 750);
    return () => window.clearInterval(timer);
  }, [playing, page?.total, loading, currentRecord, simulationId]);

  const seek = useCallback((next: number) => {
    setIndex(Math.max(0, Math.min(Math.max(0, (page?.total ?? 1) - 1), next)));
  }, [page?.total]);

  const jumpToDate = useCallback(async (date: string): Promise<boolean> => {
    const request = ++dateRequestNumber.current;
    try {
      const found = await client.findDate(date, total);
      if (request !== dateRequestNumber.current) return false;
      if (found === null) return false;
      setIndex(found);
      setError(null);
      return true;
    } catch (cause) {
      if (request === dateRequestNumber.current) setError(cause instanceof Error ? cause.message : "No se pudo buscar la fecha");
      return false;
    }
  }, [client, total]);

  const jumpToFirstCrop = useCallback(async (): Promise<boolean> => {
    const effective = resolution ?? page?.resolution ?? undefined;
    const target = firstCropNavigation(availability, effective);
    return target.status === "READY" ? jumpToDate(target.date) : false;
  }, [availability, resolution, page?.resolution, jumpToDate]);

  const loadedPage = client.loadedPage(index);
  const candidatePage = loadedPage ?? page;
  const safePage = candidatePage?.simulation_id === simulationId && (!resolution || candidatePage.resolution === resolution) ? candidatePage : null;
  const safeRecord = currentRecord?.simulation_id === simulationId && (!resolution || currentRecord.resolution === resolution) ? currentRecord : null;

  return {
    record: safeRecord, page: safePage, availability, availabilityLoading, index, seek, jumpToDate, jumpToFirstCrop,
    resolution: safePage?.resolution ?? resolution,
    setResolution, loading, error, playing, setPlaying,
    recordsForChart: safePage?.records ?? [],
  };
}
