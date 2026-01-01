// src/components/RankingTable.tsx
import React from 'react';
import type { RankingTableProps } from '../interface/RankingTableProps';

const RankingTable: React.FC<RankingTableProps> = ({ rankingData }) => {
  // Defensive checks: Ensure rankingData, rankingData.top, rankingData.bottom are defined arrays
  const topRankings = rankingData?.top || [];
  const bottomRankings = rankingData?.bottom || [];
  const properties = rankingData?.properties || []; // Also ensure properties is an array

  if (!topRankings.length && !bottomRankings.length) {
    return null; // Don't render if there's no data for top or bottom
  }

  return (
    <div className="ranking-container">
      {topRankings.length > 0 && ( // Only render Top Aquifers section if there's data
        <div className="ranking-section">
          <h3>Top Aquifers</h3>
          <table className="ranking-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>ID</th>
                {properties.map(prop => (
                  <th key={prop}>{prop}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {topRankings.map((item, index) => (
                <tr key={index} className="top-row">
                  <td>{index + 1}</td>
                  <td>{item.OBJECTID}</td>
                  {properties.map(prop => (
                    <td key={prop}>
                      {/* FIX: Check if item[prop] is a number before calling toFixed */}
                      {typeof item[prop] === 'number' ? item[prop].toFixed(4) : item[prop]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {bottomRankings.length > 0 && ( // Only render Bottom Aquifers section if there's data
        <div className="ranking-section">
          <h3>Bottom Aquifers</h3>
          <table className="ranking-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>ID</th>
                {properties.map(prop => (
                  <th key={prop}>{prop}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bottomRankings.map((item, index) => (
                <tr key={index} className="bottom-row">
                  <td>{topRankings.length + index + 1}</td> {/* Use topRankings.length here */}
                  <td>{item.OBJECTID}</td>
                  {properties.map(prop => (
                    <td key={prop}>
                      {/* FIX: Check if item[prop] is a number before calling toFixed */}
                      {typeof item[prop] === 'number' ? item[prop].toFixed(4) : item[prop]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default RankingTable;