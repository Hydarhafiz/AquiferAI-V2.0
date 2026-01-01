import type { BackendRankingData } from "./BackendRankingData";
import type { StatsData } from "./StatsData";


export interface BackendResponse {
  ai_response: string;
  statistics?: StatsData;
  cypher_queries?: string[];
  objectids?: string[];
  record_count: number;
  ranking_data?: BackendRankingData;  

}