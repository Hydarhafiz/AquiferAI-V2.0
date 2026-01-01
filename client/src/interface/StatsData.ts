// src/interface/StatsData.ts
import type { BackendRankingData } from "./BackendRankingData";
import type { OverallStats } from "./OverallStats";

export interface StatsData {
    [key: string]: any;
    overall?: OverallStats;
    ranking?: BackendRankingData;
}