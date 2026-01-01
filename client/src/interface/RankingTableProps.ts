import type { SingleRankingChunk } from "./SingleRankingChunk";

export interface RankingTableProps {
  rankingData: SingleRankingChunk; // <--- Changed to SingleRankingChunk
}