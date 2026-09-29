import type { PlaybackPage, PlaybackQuery, PlaybackRecord, PlaybackResolution } from "../types/playback";

export type PlaybackFetcher = (id: string, query: PlaybackQuery, signal: AbortSignal) => Promise<PlaybackPage>;
export const PLAYBACK_PAGE_SIZE = 100;

/** Keeps only requested pages; generation and abort both prevent cross-run stale updates. */
export class PlaybackClient {
  private fetcher: PlaybackFetcher;
  private generation = 0;
  private controller = new AbortController();
  private cache = new Map<number, PlaybackPage>();
  private pending = new Map<number, Promise<PlaybackPage | null>>();
  private id: string | null = null;
  private resolution: PlaybackResolution | undefined;

  constructor(fetcher: PlaybackFetcher) { this.fetcher = fetcher; }

  select(id: string | null, resolution?: PlaybackResolution) {
    if (this.id === id && this.resolution === resolution) return;
    this.controller.abort();
    this.controller = new AbortController();
    this.generation += 1;
    this.cache.clear();
    this.pending.clear();
    this.id = id;
    this.resolution = resolution;
  }

  async pageFor(index: number): Promise<PlaybackPage | null> {
    if (!this.id || index < 0) return null;
    const offset = Math.floor(index / PLAYBACK_PAGE_SIZE) * PLAYBACK_PAGE_SIZE;
    const cached = this.cache.get(offset);
    if (cached) return cached;
    const running = this.pending.get(offset);
    if (running) return running;
    const generation = this.generation;
    const id = this.id;
    const query: PlaybackQuery = { offset, limit: PLAYBACK_PAGE_SIZE };
    if (this.resolution) query.resolution = this.resolution;
    const promise = this.fetcher(id, query, this.controller.signal).then((page) => {
      if (generation !== this.generation || id !== this.id || this.controller.signal.aborted) return null;
      this.cache.set(offset, page);
      return page;
    }).catch((error: unknown) => {
      if (generation !== this.generation || this.controller.signal.aborted) return null;
      throw error;
    }).finally(() => { if (this.pending.get(offset) === promise) this.pending.delete(offset); });
    this.pending.set(offset, promise);
    return promise;
  }

  recordAt(index: number): PlaybackRecord | null {
    const offset = Math.floor(index / PLAYBACK_PAGE_SIZE) * PLAYBACK_PAGE_SIZE;
    return this.cache.get(offset)?.records[index - offset] ?? null;
  }

  loadedPage(index: number): PlaybackPage | null {
    return this.cache.get(Math.floor(index / PLAYBACK_PAGE_SIZE) * PLAYBACK_PAGE_SIZE) ?? null;
  }

  /** Resolve a real ISO date to its indexed record, including monthly/annual overlap. */
  async findDate(date: string, total: number): Promise<number | null> {
    if (!this.id || total <= 0) return null;
    const generation = this.generation;
    const query: PlaybackQuery = { date, limit: 1 };
    if (this.resolution) query.resolution = this.resolution;
    const match = await this.fetcher(this.id, query, this.controller.signal);
    if (generation !== this.generation || !match.records.length) return null;
    const target = match.records[0].date;
    let low = 0;
    let high = Math.ceil(total / PLAYBACK_PAGE_SIZE) - 1;
    while (low <= high) {
      const middle = Math.floor((low + high) / 2);
      const page = await this.pageFor(middle * PLAYBACK_PAGE_SIZE);
      if (generation !== this.generation || !page?.records.length) return null;
      const first = page.records[0].date;
      const last = page.records[page.records.length - 1].date;
      if (target < first) high = middle - 1;
      else if (target > last) low = middle + 1;
      else {
        const localIndex = page.records.findIndex((row) => row.date === target);
        return localIndex < 0 ? null : page.offset + localIndex;
      }
    }
    return null;
  }
}
