import React, { useState, useEffect } from 'react';
import MetricCard from '../components/MetricCard';
import Charts from '../components/Charts';
import IncidentTable from '../components/IncidentTable';
import { 
  fetchMetrics, 
  fetchIncidents,
  fetchTimeSeriesData,
  MOCK_METRICS,
  MOCK_INCIDENTS,
  MOCK_TIMESERIES 
} from '../api/incidentAPI';
import { 
  AlertTriangle, 
  Activity, 
  Cloud, 
  CloudOff,
  RefreshCw 
} from 'lucide-react';

/**
 * Dashboard - Main dashboard page with metrics, charts, and incident table
 * Auto-refreshes data every 15 seconds
 */
const Dashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [useMockData, setUseMockData] = useState(true); // Toggle for mock vs real API

  /**
   * Fetch all dashboard data
   */
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (useMockData) {
        // Use mock data for development/testing
        setMetrics(MOCK_METRICS);
        setIncidents(MOCK_INCIDENTS);
        setTimeSeriesData(MOCK_TIMESERIES);
      } else {
        // Fetch from real API
        const [metricsData, incidentsData, timeSeriesData] = await Promise.all([
          fetchMetrics(),
          fetchIncidents({ limit: 10 }),
          fetchTimeSeriesData(7)
        ]);

        setMetrics(metricsData);
        setIncidents(incidentsData);
        setTimeSeriesData(timeSeriesData);
      }

      setLastRefresh(new Date());
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message);
      
      // Fallback to mock data if API fails
      setMetrics(MOCK_METRICS);
      setIncidents(MOCK_INCIDENTS);
      setTimeSeriesData(MOCK_TIMESERIES);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchDashboardData();
  }, [useMockData]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDashboardData();
    }, 15000); // 15 seconds

    return () => clearInterval(interval);
  }, [useMockData]);

  // Manual refresh handler
  const handleRefresh = () => {
    fetchDashboardData();
  };

  // Loading state
  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="spinner mx-auto mb-4" />
          <p className="text-dark-muted">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  // Error state (with fallback data)
  if (error && !metrics) {
    return (
      <div className="bg-dark-surface border border-red-500/50 rounded-xl p-8 text-center">
        <AlertTriangle className="w-16 h-16 text-red-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-dark-text mb-2">
          Failed to Load Dashboard
        </h3>
        <p className="text-dark-muted mb-4">{error}</p>
        <button
          onClick={handleRefresh}
          className="px-6 py-2 bg-accent-primary text-white rounded-lg hover:bg-accent-primary/80 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Prepare cloud distribution for chart
  const cloudDistribution = {
    aws: metrics?.aws_incidents || 0,
    azure: metrics?.azure_incidents || 0,
    gcp: 0 // Add GCP if needed
  };

  return (
    <div className="space-y-8">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-dark-text mb-2">
            Security Dashboard
          </h1>
          <p className="text-dark-muted">
            Real-time monitoring of honeytoken activity across cloud environments
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Mock Data Toggle (for development) */}
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

          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center px-4 py-2 bg-dark-surface border border-dark-border rounded-lg hover:bg-dark-bg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            <span className="text-dark-text text-sm">Refresh</span>
          </button>
        </div>
      </div>

      {/* Last refresh indicator */}
      <div className="text-sm text-dark-muted">
        Last updated: {lastRefresh.toLocaleTimeString()}
        {!useMockData && <span className="ml-2 text-green-400">● Live</span>}
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Incidents"
          value={metrics?.total_incidents || 0}
          icon={AlertTriangle}
          color="blue"
        />
        <MetricCard
          title="Active Incidents"
          value={metrics?.active_incidents || 0}
          icon={Activity}
          color="red"
        />
        <MetricCard
          title="AWS Incidents"
          value={metrics?.aws_incidents || 0}
          icon={Cloud}
          color="orange"
        />
        <MetricCard
          title="Azure Incidents"
          value={metrics?.azure_incidents || 0}
          icon={CloudOff}
          color="blue"
        />
      </div>

      {/* Charts Section */}
      <Charts 
        timeSeriesData={timeSeriesData}
        cloudDistribution={cloudDistribution}
      />

      {/* Incidents Table */}
      <IncidentTable 
        incidents={incidents} 
        loading={loading}
      />
    </div>
  );
};

export default Dashboard;