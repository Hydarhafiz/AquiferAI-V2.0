// src/features/map/components/MapVisualization.tsx
import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './MapVisualization.css';
import type { MapVisualizationProps } from '../../interface/MapVisualizationProps';
import type { Feature } from 'geojson';


// Fix leaflet marker issue (existing code)
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'; // <-- CORRECTED THIS LINE BACK
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

L.Icon.Default.mergeOptions({
    iconUrl: markerIcon,
    iconRetinaUrl: markerIcon2x,
    shadowUrl: markerShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    tooltipAnchor: [16, -28],
    shadowSize: [41, 41]
});

// Define color mapping for risk levels
const RISK_COLORS: { [key: string]: string } = {
    "low_risk": '#28a745',
    "medium_risk": '#ffc107',
    "high_risk": '#dc3545',
    "default": '#3388ff',
};

// Define properties to exclude from the popup (fully exclude Boundary_coordinates)
const EXCLUDE_FROM_POPUP = ['Boundary_coordinates']; // Location will be handled specially

const MapVisualization: React.FC<MapVisualizationProps> = ({
    geojson,
    onFeatureClick,
    height = '500px'
}) => {
    const mapRef = useRef<L.Map | null>(null);
    const mapContainer = useRef<HTMLDivElement>(null);
    const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);
    const [selectedRiskProperty, setSelectedRiskProperty] = useState<string | null>(null);
    const [isMenuOpen, setIsMenuOpen] = useState(true);

    const toggleMenu = () => {
        setIsMenuOpen(prev => !prev);
    };

    const getFeatureStyle = useCallback((feature: Feature) => {
        let fillColor = RISK_COLORS.default;
        if (selectedRiskProperty && feature.properties) {
            const riskValue = feature.properties[selectedRiskProperty as keyof typeof feature.properties];
            fillColor = RISK_COLORS[riskValue as string] || RISK_COLORS.default;
        }
        return {
            fillColor: fillColor,
            color: "#000",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        };
    }, [selectedRiskProperty]);

    useEffect(() => {
        if (!mapContainer.current) return;

        if (!mapRef.current) {
            mapRef.current = L.map(mapContainer.current, {
                zoomControl: true,
                attributionControl: true,
                preferCanvas: true,
            }).setView([0, 0], 2);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: 18,
            }).addTo(mapRef.current);
        }

        return () => {
            if (mapRef.current) {
                mapRef.current.remove();
                mapRef.current = null;
            }
        };
    }, []);

    useEffect(() => {
        if (mapRef.current) {
            const timeoutId = setTimeout(() => {
                mapRef.current?.invalidateSize();
            }, 300);

            return () => clearTimeout(timeoutId);
        }
    }, [isMenuOpen]);

    // Inside src/features/map/components/MapVisualization.tsx
    useEffect(() => {
        if (!mapRef.current) {
            console.warn("MapVisualization: Map instance not ready.");
            return;
        }
        if (!geojson) {
            console.warn("MapVisualization: geojson prop is null or undefined.");
            return;
        }

        console.log("MapVisualization: Received GeoJSON prop:", geojson);

        if (geoJsonLayerRef.current) {
            mapRef.current.removeLayer(geoJsonLayerRef.current);
            console.log("MapVisualization: Removed existing GeoJSON layer.");
        }

        try {
            geoJsonLayerRef.current = L.geoJSON(geojson, {
                pointToLayer: (feature, latlng) => {
                    const style = getFeatureStyle(feature as Feature);
                    return L.circleMarker(latlng, { radius: 6, ...style });
                },
                style: (feature) => {
                    return getFeatureStyle(feature as Feature);
                },
                onEachFeature: (feature, layer) => {
                    if (feature.properties) {
                        const popupContent: string[] = [];
                        Object.entries(feature.properties).forEach(([key, value]) => {
                            if (EXCLUDE_FROM_POPUP.includes(key)) return; // Skip excluded

                            if (key === 'Location') {
                                try {
                                    const locationObj = JSON.parse(value as string);
                                    if (locationObj && typeof locationObj === 'object' && locationObj !== null &&
                                        typeof locationObj.latitude === 'number' && typeof locationObj.longitude === 'number') {
                                        popupContent.push(`<b>${key}:</b> Lon: ${locationObj.longitude.toFixed(4)}, Lat: ${locationObj.latitude.toFixed(4)}`);
                                    } else {
                                        popupContent.push(`<b>${key}:</b> ${value}`);
                                    }
                                } catch (e) {
                                    console.error("MapVisualization: Error parsing Location property:", e, "Value:", value);
                                    popupContent.push(`<b>${key}:</b> ${value}`);
                                }
                            } else {
                                popupContent.push(`<b>${key}:</b> ${value}`);
                            }
                        });
                        layer.bindPopup(popupContent.join('<br>'));
                        layer.on('click', () => {
                            if (onFeatureClick) {
                                onFeatureClick(feature);
                            }
                            if (geoJsonLayerRef.current) {
                                geoJsonLayerRef.current.eachLayer((l) => {
                                    if ((l as any).feature) {
                                        (l as L.Path).setStyle(getFeatureStyle((l as any).feature as Feature));
                                    }
                                });
                            }
                            (layer as L.Path).setStyle({
                                weight: 3,
                                color: '#ff0000',
                                opacity: 1,
                                fillOpacity: 0.8,
                                fillColor: getFeatureStyle(feature as Feature).fillColor
                            });
                        });
                    }
                }
            }).addTo(mapRef.current);

            console.log(`MapVisualization: Added ${geoJsonLayerRef.current?.getLayers().length} features to map.`);

            const bounds = geoJsonLayerRef.current.getBounds();
            if (bounds.isValid()) {
                console.log("MapVisualization: Fitting map to bounds:", bounds);
                const currentZoom = mapRef.current.getZoom();
                const currentCenter = mapRef.current.getCenter();
                const defaultView = currentZoom === 2 && currentCenter.lat === 0 && currentCenter.lng === 0;

                // Only fit bounds if it's the default view or current bounds don't contain new features
                if (defaultView || !mapRef.current.getBounds().contains(bounds)) {
                    mapRef.current.fitBounds(bounds, { padding: [50, 50] });
                }
            } else {
                console.warn("MapVisualization: Invalid bounds, setting default view.");
                mapRef.current.setView([0, 0], 2);
            }
        } catch (error) {
            console.error("MapVisualization: Error adding GeoJSON layer or fitting bounds:", error);
            mapRef.current.setView([0, 0], 2); // Fallback to a default view
        }

    }, [geojson, onFeatureClick, selectedRiskProperty, getFeatureStyle]);

    return (
        <div className="map-visualization-container" style={{ height }}>
            <div ref={mapContainer} className="leaflet-container" style={{ height, width: '100%' }} />

            <button
                className={`menu-toggle-button ${isMenuOpen ? 'close-button' : 'open-button'}`}
                onClick={toggleMenu}
            >
                {isMenuOpen ? '✕' : '☰'}
            </button>

            <div className={`map-controls-overlay ${isMenuOpen ? 'open' : 'closed'}`}>
                {isMenuOpen && (
                    <>
                        <div>
                            <h4>Visualize Risk By:</h4>
                            <div className="risk-button-group">
                                {['Porosity', 'Permeability', 'Depth', 'Thickness', 'Recharge', 'Lake_area'].map(prop => (
                                    <button
                                        key={prop}
                                        onClick={() => {
                                            const newRiskProperty = `${prop}_risk`;
                                            setSelectedRiskProperty(newRiskProperty);
                                        }}
                                        className={selectedRiskProperty === `${prop}_risk` ? 'active' : ''}
                                    >
                                        {prop} Risk
                                    </button>
                                ))}
                                <button
                                    onClick={() => {
                                        setSelectedRiskProperty(null);
                                    }}
                                    className={selectedRiskProperty === null ? 'active' : ''}
                                >
                                    Clear Risk
                                </button>
                            </div>
                        </div>

                        {selectedRiskProperty && (
                            <div className="map-legend">
                                <h5>Legend:</h5>
                                <div className="legend-item">
                                    <div className="legend-color-box" style={{ backgroundColor: RISK_COLORS.high_risk }}></div>
                                    <span>High Risk</span>
                                </div>
                                <div className="legend-item">
                                    <div className="legend-color-box" style={{ backgroundColor: RISK_COLORS.medium_risk }}></div>
                                    <span>Medium Risk</span>
                                </div>
                                <div className="legend-item">
                                    <div className="legend-color-box" style={{ backgroundColor: RISK_COLORS.low_risk }}></div>
                                    <span>Low Risk</span>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

export default MapVisualization;