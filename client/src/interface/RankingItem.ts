export interface RankingItem {
  OBJECTID: number;
  [key: string]: number | string | undefined | null; // Allow for dynamic properties and their types
}