import type { RankingItem } from "./RankingItem";

export interface SingleRankingChunk {
  top: RankingItem[];
  bottom: RankingItem[];
  properties: string[]; // This should be the property being ranked, e.g., ["Porosity"]
}