import React from 'react';
import { 
  Cloud, 
  User, 
  Activity, 
  Clock, 
  MapPin, 
  Globe,
  Shield,
  CheckCircle,
  XCircle,
  Download,
  AlertTriangle
} from 'lucide-react';
import { formatTimestamp, getCloudColor, getStatusColor } from '../utils/formatters';

/**
 * IncidentDetail - Detailed view component for a single incident
 * 
 * @param {Object} props
 * @param {Object} props.incident - Full incident object with all details
 */
const IncidentDetail = ({ incident }) => {
  if (!incident) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-xl p-12 text-center">
        <AlertTriangle className="w-16 h-16 text-yellow-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-dark-text">Incident Not Found</h3>
      </div>
    );
  }

  // Info row component for consistent styling
  const InfoRow = ({ icon: Icon, label, value, valueClass = '' }) => (
    <div className="flex items-start py-3 border-b border-dark-border last:border-0">
      <Icon className="w-5 h-5 text-accent-primary mr-3 mt-0.5 flex-shrink-0" />
      <div className="flex-1">
        <p className="text-sm text-dark-muted mb-1">{label}</p>
        <p className={`text-dark-text font-medium ${valueClass}`}>{value}</p>
      </div>
    </div>
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header Section */}
      <div className="bg-gradient-to-r from-dark-surface to-dark-surface/50 border border-dark-border rounded-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-dark-text mb-2">
              Incident {incident.id}
            </h2>
            <p className="text-dark-muted">
              Detected {formatTimestamp(incident.timestamp)}
            </p>
          </div>
          <span className={`
            inline-flex items-center px-4 py-2 rounded-full text-sm font-medium border
            ${getStatusColor(incident.status)}
          `}>
            {incident.status === 'Active' && (
              <span className="w-2 h-2 bg-current rounded-full mr-2 pulse-dot" />
            )}
            {incident.status}
          </span>
        </div>

        {/* Severity Badge */}
        {incident.severity && (
          <div className="inline-flex items-center px-3 py-1 rounded-lg bg-red-500/20 text-red-400 border border-red-500/50">
            <AlertTriangle className="w-4 h-4 mr-2" />
            <span className="text-sm font-medium">{incident.severity} Severity</span>
          </div>
        )}
      </div>

      {/* Basic Information */}
      <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
        <h3 className="text-lg font-semibold text-dark-text mb-4 flex items-center">
          <Shield className="w-5 h-5 mr-2 text-accent-primary" />
          Basic Information
        </h3>
        <div className="space-y-1">
          <InfoRow 
            icon={Cloud} 
            label="Cloud Provider" 
            value={
              <span className={`
                inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border
                ${getCloudColor(incident.cloud)}
              `}>
                {incident.cloud}
              </span>
            }
          />
          <InfoRow 
            icon={User} 
            label="Principal" 
            value={incident.principal}
            valueClass="font-mono text-sm"
          />
          <InfoRow 
            icon={Activity} 
            label="Trigger Type" 
            value={incident.trigger_type}
          />
          <InfoRow 
            icon={Clock} 
            label="Timestamp" 
            value={formatTimestamp(incident.timestamp)}
          />
          {incident.region && (
            <InfoRow 
              icon={MapPin} 
              label="Region" 
              value={incident.region}
            />
          )}
          {incident.ip_address && (
            <InfoRow 
              icon={Globe} 
              label="Source IP" 
              value={incident.ip_address}
              valueClass="font-mono"
            />
          )}
        </div>
      </div>

      {/* Resource Information */}
      {incident.resource_arn && (
        <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
          <h3 className="text-lg font-semibold text-dark-text mb-4">
            Resource Details
          </h3>
          <div className="bg-dark-bg rounded-lg p-4 font-mono text-sm text-dark-text break-all">
            {incident.resource_arn}
          </div>
          {incident.user_agent && (
            <div className="mt-4">
              <p className="text-sm text-dark-muted mb-2">User Agent</p>
              <div className="bg-dark-bg rounded-lg p-3 text-sm text-dark-muted font-mono">
                {incident.user_agent}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Response Actions */}
      {incident.response_actions && incident.response_actions.length > 0 && (
        <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
          <h3 className="text-lg font-semibold text-dark-text mb-4">
            Automated Response Actions
          </h3>
          <div className="space-y-3">
            {incident.response_actions.map((action, index) => (
              <div 
                key={index}
                className="flex items-start p-4 bg-dark-bg rounded-lg border border-dark-border"
              >
                {action.status === 'Success' ? (
                  <CheckCircle className="w-5 h-5 text-green-400 mr-3 mt-0.5 flex-shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-400 mr-3 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1">
                  <p className="text-dark-text font-medium mb-1">{action.action}</p>
                  <p className="text-sm text-dark-muted">
                    {formatTimestamp(action.timestamp)}
                  </p>
                </div>
                <span className={`
                  px-2 py-1 rounded text-xs font-medium
                  ${action.status === 'Success' 
                    ? 'bg-green-500/20 text-green-400' 
                    : 'bg-red-500/20 text-red-400'
                  }
                `}>
                  {action.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline */}
      {incident.timeline && incident.timeline.length > 0 && (
        <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
          <h3 className="text-lg font-semibold text-dark-text mb-6">
            Incident Timeline
          </h3>
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-accent-primary/30" />
            
            <div className="space-y-6">
              {incident.timeline.map((event, index) => (
                <div key={index} className="relative pl-8">
                  {/* Timeline dot */}
                  <div className="absolute left-0 top-1 w-4 h-4 rounded-full bg-accent-primary border-4 border-dark-surface" />
                  
                  <div className="bg-dark-bg rounded-lg p-4 border border-dark-border">
                    <p className="text-dark-text font-medium mb-1">{event.event}</p>
                    <p className="text-sm text-dark-muted">
                      {formatTimestamp(event.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Evidence Bundle */}
      {incident.evidence && Object.keys(incident.evidence).length > 0 && (
        <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
          <h3 className="text-lg font-semibold text-dark-text mb-4">
            Evidence Bundle
          </h3>
          <div className="space-y-2">
            {Object.entries(incident.evidence).map(([key, url]) => (
              <a
                key={key}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between p-3 bg-dark-bg rounded-lg border border-dark-border hover:border-accent-primary transition-colors group"
              >
                <div className="flex items-center">
                  <Download className="w-5 h-5 text-accent-primary mr-3" />
                  <span className="text-dark-text group-hover:text-accent-primary transition-colors">
                    {key.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </div>
                <span className="text-dark-muted text-sm">
                  View →
                </span>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Threat Indicators */}
      {incident.threat_indicators && (
        <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
          <h3 className="text-lg font-semibold text-dark-text mb-4">
            Threat Intelligence
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-dark-bg rounded-lg p-4 text-center">
              <p className="text-dark-muted text-sm mb-2">VPN Detected</p>
              <p className={`font-semibold ${incident.threat_indicators.is_vpn ? 'text-red-400' : 'text-green-400'}`}>
                {incident.threat_indicators.is_vpn ? 'Yes' : 'No'}
              </p>
            </div>
            <div className="bg-dark-bg rounded-lg p-4 text-center">
              <p className="text-dark-muted text-sm mb-2">Tor Network</p>
              <p className={`font-semibold ${incident.threat_indicators.is_tor ? 'text-red-400' : 'text-green-400'}`}>
                {incident.threat_indicators.is_tor ? 'Yes' : 'No'}
              </p>
            </div>
            <div className="bg-dark-bg rounded-lg p-4 text-center">
              <p className="text-dark-muted text-sm mb-2">Known Attacker</p>
              <p className={`font-semibold ${incident.threat_indicators.is_known_attacker ? 'text-red-400' : 'text-green-400'}`}>
                {incident.threat_indicators.is_known_attacker ? 'Yes' : 'No'}
              </p>
            </div>
            <div className="bg-dark-bg rounded-lg p-4 text-center">
              <p className="text-dark-muted text-sm mb-2">Location</p>
              <p className="font-semibold text-dark-text">
                {incident.threat_indicators.geo_location || 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IncidentDetail;
