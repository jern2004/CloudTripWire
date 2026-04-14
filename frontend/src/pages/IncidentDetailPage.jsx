import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import IncidentDetail from '../components/IncidentDetail';
import {
  fetchIncidentById,
  markIncidentResolved,
  MOCK_INCIDENT_DETAIL
} from '../api/incidentAPI';
import { ArrowLeft, CheckCircle, Loader, XCircle } from 'lucide-react';

/**
 * IncidentDetailPage - Full page view for single incident with actions
 */
const IncidentDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resolving, setResolving] = useState(false);
  const [useMockData, setUseMockData] = useState(false);
  // Inline notification: { type: 'success' | 'error', message: string } | null
  const [notification, setNotification] = useState(null);

  /**
   * Fetch incident details
   */
  useEffect(() => {
    const fetchIncident = async () => {
      try {
        setLoading(true);
        setError(null);

        if (useMockData) {
          // Use mock data
          setIncident({ ...MOCK_INCIDENT_DETAIL, id });
        } else {
          // Fetch from real API
          const data = await fetchIncidentById(id);
          setIncident(data);
        }
      } catch (err) {
        console.error('Error fetching incident:', err);
        setError(err.message);
        
        // Fallback to mock data
        setIncident({ ...MOCK_INCIDENT_DETAIL, id });
      } finally {
        setLoading(false);
      }
    };

    fetchIncident();
  }, [id, useMockData]);

  /**
   * Handle marking incident as resolved
   */
  const handleMarkResolved = async () => {
    try {
      setResolving(true);
      setNotification(null);

      if (!useMockData) {
        await markIncidentResolved(id);
      }

      // Update local state to reflect resolved status
      setIncident(prev => ({ ...prev, status: 'Resolved' }));
      setNotification({ type: 'success', message: 'Incident marked as resolved successfully.' });

      // Auto-dismiss after 5 seconds
      setTimeout(() => setNotification(null), 5000);
    } catch (err) {
      console.error('Error resolving incident:', err);
      setNotification({ type: 'error', message: `Failed to resolve incident: ${err.message}` });
    } finally {
      setResolving(false);
    }
  };

  /**
   * Navigate back to dashboard
   */
  const handleBackClick = () => {
    navigate('/');
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="spinner mx-auto mb-4" />
          <p className="text-dark-muted">Loading incident details...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !incident) {
    return (
      <div className="bg-dark-surface border border-red-500/50 rounded-xl p-8 text-center">
        <h3 className="text-xl font-semibold text-dark-text mb-2">
          Failed to Load Incident
        </h3>
        <p className="text-dark-muted mb-4">{error}</p>
        <button
          onClick={handleBackClick}
          className="px-6 py-2 bg-accent-primary text-white rounded-lg hover:bg-accent-primary/80 transition-colors"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <button
          onClick={handleBackClick}
          className="flex items-center text-dark-muted hover:text-dark-text transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </button>

        <div className="flex items-center space-x-3">
          {/* Mock Data Toggle */}
          <button
            onClick={() => setUseMockData(!useMockData)}
            className={`
              px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${useMockData 
                ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/50' 
                : 'bg-green-500/20 text-green-400 border border-green-500/50'
              }
            `}
          >
            {useMockData ? '📊 Mock Data' : '🔗 Live API'}
          </button>

          {/* Mark Resolved Button */}
          {incident?.status === 'Active' && (
            <button
              onClick={handleMarkResolved}
              disabled={resolving}
              className="flex items-center px-6 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {resolving ? (
                <>
                  <Loader className="w-4 h-4 mr-2 animate-spin" />
                  Resolving...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Mark as Resolved
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Inline notification banner — replaces browser alert() */}
      {notification && (
        <div className={`
          flex items-center justify-between px-4 py-3 rounded-lg border animate-fade-in
          ${notification.type === 'success'
            ? 'bg-green-500/10 border-green-500/50 text-green-400'
            : 'bg-red-500/10 border-red-500/50 text-red-400'
          }
        `}>
          <div className="flex items-center">
            {notification.type === 'success'
              ? <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
              : <XCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            }
            <span className="text-sm font-medium">{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="ml-4 text-current opacity-60 hover:opacity-100 transition-opacity"
            aria-label="Dismiss notification"
          >
            ×
          </button>
        </div>
      )}

      {/* Incident Detail Component */}
      <IncidentDetail incident={incident} />
    </div>
  );
};

export default IncidentDetailPage;