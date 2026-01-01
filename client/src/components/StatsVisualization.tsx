// src/components/StatsVisualization.tsx
import React, { useState, useEffect } from 'react'; // <--- Import useEffect
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ComposedChart, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LabelList
} from 'recharts';
import type { StatsVisualizationProps } from '../interface/StatsVisualizationProps';
import './StatsVisualization.css';
import type { StatsData } from '../interface/StatsData';
import type { RiskCounts } from '../interface/RiskCounts';
import type { PropertyStats } from '../interface/PropertyStats';

const StatsVisualization: React.FC<StatsVisualizationProps> = ({ stats }) => {
  const [viewMode, setViewMode] = useState<'property' | 'statistic'>('property');
  const [selectedProperty, setSelectedProperty] = useState<string | null>(null);

  // NEW STATE FOR OUTLIER TABLE SELECTION
  const [selectedOutlierProperty, setSelectedOutlierProperty] = useState<string | null>(null); // <--- NEW

  // Helper to get emojis
  const getRiskEmoji = (riskType: 'low' | 'medium' | 'high') => {
    switch (riskType) {
      case 'low': return '🟢';
      case 'medium': return '🟡';
      case 'high': return '🔴';
      default: return '';
    }
  };

  // Function to safely get actual stats (updated to handle 'overall' and 'risk')
  const getActualStats = (): StatsData => {
    if (!stats || typeof stats !== 'object' || Array.isArray(stats)) return {};

    const keys = Object.keys(stats);
    if (keys.length === 0) return {};

    if (stats.overall && typeof stats.overall === 'object' && !Array.isArray(stats.overall)) {
        return stats.overall as StatsData;
    }

    return stats;
  };

  const actualStats = getActualStats();

  const riskData: { [property: string]: RiskCounts } | undefined = (actualStats as any).risk;

  const propertyList = Object.keys(actualStats).filter(key =>
    actualStats[key] && typeof actualStats[key] === 'object' && 'mean' in actualStats[key]
  );

  // Data for property-focused view
  const propertyChartData = propertyList.map(property => {
    const data = actualStats[property] as PropertyStats;
    return {
      property,
      min: data.min,
      max: data.max,
      mean: data.mean,
      p5: data.p5,
      p25: data.p25,
      p50: data.p50,
      p75: data.p75,
      p95: data.p95,
    };
  });

  // Data for statistic-focused view
  const statisticChartData = [
    { name: 'min', ...Object.fromEntries(propertyList.map(p => [p, (actualStats[p] as PropertyStats).min])) },
    { name: 'max', ...Object.fromEntries(propertyList.map(p => [p, (actualStats[p] as PropertyStats).max])) },
    { name: 'mean', ...Object.fromEntries(propertyList.map(p => [p, (actualStats[p] as PropertyStats).mean])) },
    { name: 'p5', ...Object.fromEntries(propertyList.map(p => [p, (actualStats[p] as PropertyStats).p5])) },
    { name: 'p25', ...Object.fromEntries(propertyList.map(p => [p, (actualStats[p] as PropertyStats).p25])) },
    { name: 'p50', ...Object.fromEntries(propertyList.map(p => [p, (actualStats[p] as PropertyStats).p50])) },
    { name: 'p75', ...Object.fromEntries(propertyList.map(p => [p, (actualStats[p] as PropertyStats).p75])) },
    { name: 'p95', ...Object.fromEntries(propertyList.map(p => [p, (actualStats[p] as PropertyStats).p95])) },
  ];

  // Radar chart data for comparison
  const radarChartData = propertyList.map(property => {
    const data = actualStats[property] as PropertyStats;
    return {
      property,
      min: data.min,
      max: data.max,
      mean: data.mean,
      A: data.mean,
      B: (data.max - data.min) / 2,
    };
  });

  // NEW: Prepare outlier data, grouped by property
  const groupedOutlierData: { [key: string]: Array<{ OBJECTID: number; value: number; z_score: number; }> } = {};
  Object.entries(actualStats).forEach(([property, data]) => {
    if ((data as PropertyStats).outliers && (data as PropertyStats).outliers!.length > 0) {
      groupedOutlierData[property] = (data as PropertyStats).outliers!.map((outlier: any) => ({
        OBJECTID: outlier.OBJECTID,
        value: outlier.value,
        z_score: outlier.z_score,
      }));
    }
  });

  // Get a list of properties that actually have outliers
  const outlierProperties = Object.keys(groupedOutlierData);

  // Effect to set the first outlier property as selected by default
  useEffect(() => {
    if (outlierProperties.length > 0 && selectedOutlierProperty === null) {
      setSelectedOutlierProperty(outlierProperties[0]);
    }
  }, [outlierProperties, selectedOutlierProperty]); // <--- Dependency array for useEffect

  // Check if we have valid chart data OR outlier data
  if (!propertyList.length && !riskData && outlierProperties.length === 0) { // <--- Added outlierProperties check
    return (
      <div className="stats-visualization">
        <h3>Statistical Analysis</h3>
        <p>No visualization data available for this response.</p>
      </div>
    );
  }

  // Property color mapping
  const propertyColors = {
    Porosity: '#8884d8',
    Permeability: '#82ca9d',
    Depth: '#ffc658',
    Thickness: '#ff7300',
    Recharge: '#00C49F',
    Lake_area: '#0088FE',
  };

  return (
    <div className="stats-visualization">
      <h3>Statistical Analysis</h3>

      <div className="visualization-controls">
        <button
          onClick={() => setViewMode('property')}
          className={viewMode === 'property' ? 'active' : ''}
        >
          Property View
        </button>
        <button
          onClick={() => setViewMode('statistic')}
          className={viewMode === 'statistic' ? 'active' : ''}
        >
          Statistic View
        </button>
      </div>

      {viewMode === 'property' ? (
        <div className="property-view">
          <div className="property-selector">
            {propertyList.map(property => (
              <button
                key={property}
                onClick={() => setSelectedProperty(selectedProperty === property ? null : property)}
                className={selectedProperty === property ? 'active' : ''}
              >
                {property}
              </button>
            ))}
          </div>

          {selectedProperty ? (
            <div className="property-detail">
              <h4>{selectedProperty} Distribution</h4>
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart
                  data={[actualStats[selectedProperty as keyof StatsData]]}
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="property" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="min" name="Minimum" fill="#8884d8" />
                  <Bar dataKey="max" name="Maximum" fill="#82ca9d" />
                  <Bar dataKey="p5" name="5th Percentile" fill="#ffc658" />
                  <Bar dataKey="p25" name="25th Percentile" fill="#ff7300" />
                  <Bar dataKey="p50" name="50th Percentile" fill="#00C49F" />
                  <Bar dataKey="p75" name="75th Percentile" fill="#0088FE" />
                  <Bar dataKey="p95" name="95th Percentile" fill="#FF8042" />
                  <Bar dataKey="mean" name="Mean" fill="#000000">
                    <LabelList
                      dataKey="mean"
                      position="top"
                      formatter={(value: number) => Number(value).toFixed(3)}
                      style={{ fill: '#333', fontSize: 14, fontWeight: 'bold' }}
                    />
                  </Bar>
                </ComposedChart>
              </ResponsiveContainer>

              <div className="stat-values">
                <h5>Detailed Values:</h5>
                <ul>
                  <li><strong>Min:</strong> {((actualStats[selectedProperty as keyof StatsData] as PropertyStats).min).toFixed(4)}</li>
                  <li><strong>Max:</strong> {((actualStats[selectedProperty as keyof StatsData] as PropertyStats).max).toFixed(4)}</li>
                  <li><strong>Mean:</strong> {((actualStats[selectedProperty as keyof StatsData] as PropertyStats).mean).toFixed(4)}</li>
                  <li><strong>5th Percentile:</strong> {((actualStats[selectedProperty as keyof StatsData] as PropertyStats).p5).toFixed(4)}</li>
                  <li><strong>25th Percentile:</strong> {((actualStats[selectedProperty as keyof StatsData] as PropertyStats).p25).toFixed(4)}</li>
                  <li><strong>50th Percentile:</strong> {((actualStats[selectedProperty as keyof StatsData] as PropertyStats).p50).toFixed(4)}</li>
                  <li><strong>75th Percentile:</strong> {((actualStats[selectedProperty as keyof StatsData] as PropertyStats).p75).toFixed(4)}</li>
                  <li><strong>95th Percentile:</strong> {((actualStats[selectedProperty as keyof StatsData] as PropertyStats).p95).toFixed(4)}</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="overview-charts">
              <div className="chart-container">
                <h4>Property Comparison</h4>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarChartData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="property" />
                    <PolarRadiusAxis />
                    <Radar name="Mean" dataKey="A" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-container">
                <h4>Property Ranges</h4>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={propertyChartData} margin={{ top: 20, right: 30, left: 20, bottom: 70 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="property" angle={-45} textAnchor="end" height={70} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="min" name="Min" fill="#8884d8" />
                    <Bar dataKey="max" name="Max" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="statistic-view">
          <div className="chart-container">
            <h4>Statistical Distribution by Property</h4>
            <ResponsiveContainer width="100%" height={500}>
              <BarChart
                data={statisticChartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 70 }}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={100} />
                <Tooltip />
                <Legend />
                {propertyList.map(property => (
                  <Bar
                    key={property}
                    dataKey={property}
                    name={property}
                    fill={propertyColors[property as keyof typeof propertyColors] || '#8884d8'}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-container">
            <h4>Mean Values Comparison</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={propertyChartData} margin={{ top: 20, right: 30, left: 20, bottom: 70 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="property" angle={-45} textAnchor="end" height={70} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="mean" name="Mean" fill="#ff7300" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* NEW: Outliers Table - now divided by property */}
      {outlierProperties.length > 0 && (
        <div className="outliers-container">
          <h4>Statistical Outliers (|z-score| &gt; 2.5)</h4>

          <div className="property-selector"> {/* Re-using the existing CSS class for buttons */}
            {outlierProperties.map(property => (
              <button
                key={`outlier-prop-${property}`}
                onClick={() => setSelectedOutlierProperty(property)}
                className={selectedOutlierProperty === property ? 'active' : ''}
              >
                {property}
              </button>
            ))}
          </div>

          {selectedOutlierProperty && groupedOutlierData[selectedOutlierProperty] ? (
            <table className="outliers-table">
              <thead>
                <tr>
                  <th>Aquifer ID</th>
                  <th>Value</th>
                  <th>Z-Score</th>
                </tr>
              </thead>
              <tbody>
                {groupedOutlierData[selectedOutlierProperty].map((outlier, index) => (
                  <tr key={index}>
                    <td>{outlier.OBJECTID}</td>
                    <td>{Number(outlier.value).toFixed(4)}</td>
                    <td>{Number(outlier.z_score).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="select-property-message">Select a property above to view its outliers.</p>
          )}
        </div>
      )}

      {/* Risk Level Table */}
      {riskData && Object.keys(riskData).length > 0 && (
        <div className="risk-level-container">
          <h4>Aquifer Risk Level Distribution by Property</h4>
          <table className="risk-level-table">
            <thead>
              <tr>
                <th>Property</th>
                <th>{getRiskEmoji('low')} Low Risk</th>
                <th>{getRiskEmoji('medium')} Medium Risk</th>
                <th>{getRiskEmoji('high')} High Risk</th>
                <th>Total Assessed</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(riskData).map(([property, counts]) => (
                <tr key={property}>
                  <td>{property}</td>
                  <td>{counts.low_risk_count}</td>
                  <td>{counts.medium_risk_count}</td>
                  <td>{counts.high_risk_count}</td>
                  <td>{counts.total_aquifers_assessed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default StatsVisualization;