import React from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { formatChartDate } from '../utils/formatters';
import { TrendingUp, BarChart3 } from 'lucide-react';

/**
 * Custom Tooltip for charts
 */
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-lg p-3 shadow-xl">
        <p className="text-dark-text font-medium mb-1">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: <span className="font-semibold">{entry.value}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * IncidentsOverTimeChart - Line chart showing incident trends
 * 
 * @param {Object} props
 * @param {Array} props.data - Time series data [{date, count}]
 */
export const IncidentsOverTimeChart = ({ data }) => {
  // Transform data for chart
  const chartData = data.map(item => ({
    date: formatChartDate(item.date),
    incidents: item.count
  }));

  return (
    <div className="bg-dark-surface border border-dark-border rounded-xl p-6 animate-fade-in">
      <div className="flex items-center mb-6">
        <TrendingUp className="w-5 h-5 mr-2 text-accent-primary" />
        <h3 className="text-lg font-semibold text-dark-text">
          Incidents Over Time
        </h3>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis 
            dataKey="date" 
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ fontSize: '14px', color: '#e2e8f0' }}
          />
          <Line
            type="monotone"
            dataKey="incidents"
            stroke="#38bdf8"
            strokeWidth={3}
            dot={{ fill: '#38bdf8', r: 4 }}
            activeDot={{ r: 6 }}
            name="Incidents"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

/**
 * IncidentsByCloudChart - Bar chart showing incidents by cloud provider
 * 
 * @param {Object} props
 * @param {Object} props.data - Cloud distribution data {aws, azure, gcp}
 */
export const IncidentsByCloudChart = ({ data }) => {
  // Transform data for chart
  const chartData = [
    { cloud: 'AWS', incidents: data.aws || 0, fill: '#FF9900' },
    { cloud: 'Azure', incidents: data.azure || 0, fill: '#0078D4' },
    { cloud: 'GCP', incidents: data.gcp || 0, fill: '#4285F4' },
  ].filter(item => item.incidents > 0); // Only show clouds with incidents

  return (
    <div className="bg-dark-surface border border-dark-border rounded-xl p-6 animate-fade-in">
      <div className="flex items-center mb-6">
        <BarChart3 className="w-5 h-5 mr-2 text-accent-secondary" />
        <h3 className="text-lg font-semibold text-dark-text">
          Incidents by Cloud Provider
        </h3>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis 
            dataKey="cloud" 
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ fontSize: '14px', color: '#e2e8f0' }}
          />
          <Bar 
            dataKey="incidents" 
            fill="#818cf8"
            radius={[8, 8, 0, 0]}
            name="Incidents"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

/**
 * Charts - Container component for both charts
 */
const Charts = ({ timeSeriesData, cloudDistribution }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <IncidentsOverTimeChart data={timeSeriesData} />
      <IncidentsByCloudChart data={cloudDistribution} />
    </div>
  );
};

export default Charts;