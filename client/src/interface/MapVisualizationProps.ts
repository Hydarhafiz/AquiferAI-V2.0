import type { FeatureCollection, GeoJsonProperties, Geometry } from 'geojson'; // Make sure to import FeatureCollection

export interface MapVisualizationProps {
  // Explicitly require FeatureCollection, not the broader GeoJSON type
  geojson: FeatureCollection<Geometry, GeoJsonProperties>; 
  onFeatureClick?: (feature: any) => void;
  height?: string;
}