import React, { useState, useEffect, useCallback } from 'react';
import IncidentTable from '../components/IncidentTable';
import { fetchIncidents, MOCK_INCIDENTS } from '../api/incidentAPI';
import { AlertTriangle, Search, RefreshCw, Filter } from 'lucide-react';

/**
 * IncidentsPage — full incident list with search, cloud filter, and status filter.
 * Route: /incidents
 */
const IncidentsPage = () => {
  const [allIncidents, setAllIncidents]   = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [useMockData, setUseMockData]     = useState(true);

  // Filter state
  const [search, setSearch]               = useState('');
  const [cloudFilter, setCloudFilter]     = useState('All');
  const [statusFilter, setStatusFilter]   = useState('All');

  // ── Data fetching ────────────────────────────────────────────────────────────

  const loadIncidents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      if (useMockData) {
        setAllIncidents(MOCK_INCIDENTS);
      } else {
        // Fetch up to 100; client-side filtering handles the rest
        const data = await fetchIncidents({ limit: 100 });
        setAllIncidents(data);
      }
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
      setError(err.message);
      setAllIncidents(MOCK_INCIDENTS); // fallback
    } finally {
      setLoading(false);
    }
  }, [useMockData]);

  useEffect(() => { loadIncidents(); }, [loadIncidents]);

  // ── Client-side filtering ────────────────────────────────────────────────────

  const filtered = allIncidents.filter((inc) => {
    const matchesCloud  = cloudFilter  === 'All' || inc.cloud   === cloudFilter;
    const matchesStatus = statusFilter === 'All' || inc.status  === statusFilter;
    const needle        = search.toLowerCase();
    const matchesSearch =
      !needle ||
      inc.id.toLowerCase().includes(needle)            ||
      inc.principal.toLowerCase().includes(needle)     ||
      inc.trigger_type.toLowerCase().includes(needle)  ||
      (inc.ip_address || '').toLowerCase().includes(needle);

    return matchesCloud && matchesStatus && matchesSearch;
  });

  // ── Derived counts for summary badges ───────────────────────────────────────

  const activeCount = allIncidents.filter((i) => i.status === 'Active').length;
  const awsCount    = allIncidents.filter((i) => i.cloud  === 'AWS').length;
  const azureCount  = allIncidents.filter((i) => i.cloud  === 'Azure').length;

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">

      {/* ── Page header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-dark-text flex items-center gap-3">
            <AlertTriangle className="w-8 h-8 text-accent-warning" />
            All Incidents
          </h1>
          <p className="text-dark-muted mt-1">
            Complete incident log across all cloud environments
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Mock / Live toggle */}
          <button
            onClick={() => setUseMockData(!useMockData)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${useMockData
                ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/50'
                : 'bg-green-500/20 text-green-400 border border-green-500/50'
              }`}
          >
            {useMockData ? 'Mock Data' : 'Live API'}
          </button>

          <button
            onClick={loadIncidents}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-dark-surface border border-dark-border rounded-lg hover:bg-dark-bg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="text-dark-text text-sm">Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Summary badges ── */}
      <div className="flex flex-wrap gap-3">
        <span className="px-3 py-1.5 rounded-lg bg-dark-surface border border-dark-border text-sm text-dark-muted">
          Total: <span className="font-semibold text-dark-text">{allIncidents.length}</span>
        </span>
        <span className="px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
          Active: <span className="font-semibold">{activeCount}</span>
        </span>
        <span className="px-3 py-1.5 rounded-lg bg-orange-500/10 border border-orange-500/30 text-sm text-orange-400">
          AWS: <span className="font-semibold">{awsCount}</span>
        </span>
        <span className="px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/30 text-sm text-blue-400">
          Azure: <span className="font-semibold">{azureCount}</span>
        </span>
      </div>

      {/* ── Filter bar ── */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-muted" />
          <input
            type="text"
            placeholder="Search by ID, principal, trigger type, or IP..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 bg-dark-surface border border-dark-border rounded-lg
                       text-dark-text placeholder-dark-muted text-sm
                       focus:outline-none focus:border-accent-primary transition-colors"
          />
        </div>

        {/* Cloud filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-dark-muted flex-shrink-0" />
          <select
            value={cloudFilter}
            onChange={(e) => setCloudFilter(e.target.value)}
            className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2.5
                       text-dark-text text-sm focus:outline-none focus:border-accent-primary
                       transition-colors cursor-pointer"
          >
            <option value="All">All Clouds</option>
            <option value="AWS">AWS</option>
            <option value="Azure">Azure</option>
          </select>
        </div>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2.5
                     text-dark-text text-sm focus:outline-none focus:border-accent-primary
                     transition-colors cursor-pointer"
        >
          <option value="All">All Statuses</option>
          <option value="Active">Active</option>
          <option value="Resolved">Resolved</option>
        </select>
      </div>

      {/* ── Filter result count ── */}
      {(search || cloudFilter !== 'All' || statusFilter !== 'All') && !loading && (
        <p className="text-sm text-dark-muted animate-fade-in">
          Showing{' '}
          <span className="font-medium text-dark-text">{filtered.length}</span>
          {' '}of{' '}
          <span className="font-medium text-dark-text">{allIncidents.length}</span>
          {' '}incidents
          {search && (
            <span> matching <span className="text-accent-primary">"{search}"</span></span>
          )}
        </p>
      )}

      {/* ── Error banner ── */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error} — showing mock data as fallback.
        </div>
      )}

      {/* ── Incident table ── */}
      <IncidentTable incidents={filtered} loading={loading} />
    </div>
  );
};

export default IncidentsPage;
