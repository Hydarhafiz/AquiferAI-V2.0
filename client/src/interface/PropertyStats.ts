export interface PropertyStats {
  count: number;
  mean: number;
  min: number;
  max: number;
  std_dev: number;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
  outliers?: Array<{
    OBJECTID: number;
    value: number;
    z_score: number;
  }>;
}