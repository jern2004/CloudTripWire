import React from 'react';
import { useNavigate } from 'react-router-dom';
import { formatTimestamp, getStatusColor, getCloudColor, truncateString } from '../utils/formatters';
import { AlertTriangle, CheckCircle, ExternalLink } from 'lucide-react';

/**
 * IncidentTable - Displays recent incidents in a responsive table
 * 
 * @param {Object} props
 * @param {Array} props.incidents - Array of incident objects
 * @param {boolean} props.loading - Loading state
 */
const IncidentTable = ({ incidents, loading }) => {
  const navigate = useNavigate();

  // Handle row click to navigate to detail page
  const handleRowClick = (incidentId) => {
    navigate(`/incident/${incidentId}`);
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-dark-border rounded w-1/4 mb-4"></div>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-dark-border rounded mb-2"></div>
          ))}
        </div>
      </div>
    );
  }

  // Empty state
  if (!incidents || incidents.length === 0) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-xl p-12 text-center">
        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-dark-text mb-2">No Incidents Found</h3>
        <p className="text-dark-muted">All honeytokens are secure. No suspicious activity detected.</p>
      </div>
    );
  }

  return (
    <div className="bg-dark-surface border border-dark-border rounded-xl overflow-hidden animate-slide-up">
      {/* Table Header */}
      <div className="px-6 py-4 border-b border-dark-border">
        <h2 className="text-xl font-semibold text-dark-text flex items-center">
          <AlertTriangle className="w-5 h-5 mr-2 text-accent-warning" />
          Recent Incidents
        </h2>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-dark-bg/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-dark-muted uppercase tracking-wider">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-dark-muted uppercase tracking-wider">
                Cloud
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-dark-muted uppercase tracking-wider">
                Principal
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-dark-muted uppercase tracking-wider">
                Trigger Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-dark-muted uppercase tracking-wider">
                Timestamp
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-dark-muted uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-dark-muted uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-border">
            {incidents.map((incident) => (
              <tr
                key={incident.id}
                onClick={() => handleRowClick(incident.id)}
                className="table-row-hover transition-colors"
              >
                {/* Incident ID */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm font-mono text-accent-primary">
                    {incident.id}
                  </span>
                </td>

                {/* Cloud Provider */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`
                    inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border
                    ${getCloudColor(incident.cloud)}
                  `}>
                    {incident.cloud}
                  </span>
                </td>

                {/* Principal */}
                <td className="px-6 py-4">
                  <span className="text-sm text-dark-text font-mono">
                    {truncateString(incident.principal, 40)}
                  </span>
                </td>

                {/* Trigger Type */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-dark-text">
                    {incident.trigger_type}
                  </span>
                </td>

                {/* Timestamp */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-dark-muted">
                    {formatTimestamp(incident.timestamp)}
                  </span>
                </td>

                {/* Status */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`
                    inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border
                    ${getStatusColor(incident.status)}
                  `}>
                    {incident.status === 'Active' && (
                      <span className="w-2 h-2 bg-current rounded-full mr-1.5 pulse-dot" />
                    )}
                    {incident.status}
                  </span>
                </td>

                {/* Action */}
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <button 
                    className="text-accent-primary hover:text-accent-primary/80 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRowClick(incident.id);
                    }}
                  >
                    <ExternalLink className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Table Footer */}
      <div className="px-6 py-4 border-t border-dark-border bg-dark-bg/30">
        <p className="text-sm text-dark-muted">
          Showing <span className="font-medium text-dark-text">{incidents.length}</span> incidents
        </p>
      </div>
    </div>
  );
};

export default IncidentTable;