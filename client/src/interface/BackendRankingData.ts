import type { SingleRankingChunk } from "./SingleRankingChunk";

export interface BackendRankingData { // Renamed to avoid confusion
  [key: string]: SingleRankingChunk;
}