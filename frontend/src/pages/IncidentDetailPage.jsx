import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import IncidentDetail from '../components/IncidentDetail';
import { 
  fetchIncidentById, 
  markIncidentResolved,
  MOCK_INCIDENT_DETAIL 
} from '../api/incidentAPI';
import { ArrowLeft, CheckCircle, Loader } from 'lucide-react';

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
  const [useMockData, setUseMockData] = useState(true);

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
      
      if (!useMockData) {
        await markIncidentResolved(id);
      }
      
      // Update local state
      setIncident(prev => ({ ...prev, status: 'Resolved' }));
      
      // Show success message (you can add a toast notification here)
      alert('Incident marked as resolved successfully!');
    } catch (err) {
      console.error('Error resolving incident:', err);
      alert(`Failed to resolve incident: ${err.message}`);
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

      {/* Incident Detail Component */}
      <IncidentDetail incident={incident} />
    </div>
  );
};

export default IncidentDetailPage;