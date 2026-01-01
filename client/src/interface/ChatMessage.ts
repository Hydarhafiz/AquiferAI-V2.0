import type { BackendRankingData } from "./BackendRankingData";
import type { StatsData } from "./StatsData";
import type { FeatureCollection, GeoJsonProperties, Geometry } from 'geojson';

export interface ChatMessage {
  user: string;
  bot: {
    ranking_data?: BackendRankingData;
    text: string;
    stats?: StatsData;
    spatialData?: FeatureCollection<Geometry, GeoJsonProperties>;
    cypherQueries?: string[];
  };
}