// src/features/map/services/MapService.ts
import { postRequest } from './httpService';
import type { FeatureCollection, GeoJsonProperties, Geometry } from 'geojson';

export const fetchSpatialData = async (
  objectids: string[], 
  properties: string[] = ['OBJECTID', 'Porosity', 'Permeability', 'Depth', 'Thickness', 'Recharge', 'Lake_area']
): Promise<FeatureCollection<Geometry, GeoJsonProperties> | null> => { // <--- ENSURE THIS TYPE
  try {
    const response = await postRequest<{ 
      objectids: string[];
      properties: string[];
    }, FeatureCollection<Geometry, GeoJsonProperties> | { error: string }>( // <--- ENSURE THIS TYPE
      '/api/aquifer-spatial',
      { objectids, properties }
    );
    
    if (response && 'error' in response) {
      console.error('Error fetching spatial data:', response.error);
      return null;
    }
    
    // Explicitly cast to FeatureCollection for type safety
    return response as FeatureCollection<Geometry, GeoJsonProperties>; 
  } catch (error) {
    console.error('Map service error:', error);
    return null;
  }
};