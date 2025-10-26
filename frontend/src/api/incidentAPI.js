import axios from 'axios';

/**
 * Axios instance configured for CloudTripwire API
 */
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor for adding auth tokens (if needed in future)
 */
api.interceptors.request.use(
  (config) => {
    // Add auth token here if needed
    // const token = localStorage.getItem('token');
    // if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Response interceptor for global error handling
 */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

/**
 * Fetch dashboard metrics
 * @returns {Promise} Metrics data object
 */
export const fetchMetrics = async () => {
  try {
    const response = await api.get('/metrics');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch metrics: ${error.message}`);
  }
};

/**
 * Fetch all incidents with optional filters
 * @param {Object} params - Query parameters (limit, status, cloud)
 * @returns {Promise} Array of incidents
 */
export const fetchIncidents = async (params = {}) => {
  try {
    const response = await api.get('/incidents', { params });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch incidents: ${error.message}`);
  }
};

/**
 * Fetch single incident by ID
 * @param {string} id - Incident ID
 * @returns {Promise} Incident object
 */
export const fetchIncidentById = async (id) => {
  try {
    const response = await api.get(`/incident/${id}`);
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch incident ${id}: ${error.message}`);
  }
};

/**
 * Update incident status to resolved
 * @param {string} id - Incident ID
 * @returns {Promise} Updated incident object
 */
export const markIncidentResolved = async (id) => {
  try {
    const response = await api.patch(`/incident/${id}`, { status: 'Resolved' });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to update incident ${id}: ${error.message}`);
  }
};

/**
 * Fetch time-series data for charts
 * @param {number} days - Number of days to fetch
 * @returns {Promise} Time-series data array
 */
export const fetchTimeSeriesData = async (days = 7) => {
  try {
    const response = await api.get('/incidents/timeseries', { params: { days } });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch time-series data: ${error.message}`);
  }
};

// ========== MOCK DATA (for testing without backend) ==========

/**
 * Mock metrics data
 */
export const MOCK_METRICS = {
  total_incidents: 47,
  active_incidents: 12,
  aws_incidents: 28,
  azure_incidents: 19,
  resolved_incidents: 35,
  avg_response_time: 142 // seconds
};

/**
 * Mock incidents array
 */
export const MOCK_INCIDENTS = [
  {
    id: 'inc-001',
    cloud: 'AWS',
    principal: 'arn:aws:iam::123456789012:user/honeypot-user',
    trigger_type: 'S3 Access',
    timestamp: '2025-10-27T14:23:45Z',
    status: 'Active',
    severity: 'High',
    ip_address: '203.45.67.89',
    region: 'us-east-1'
  },
  {
    id: 'inc-002',
    cloud: 'Azure',
    principal: 'decoy-service-principal@contoso.com',
    trigger_type: 'Key Vault Access',
    timestamp: '2025-10-27T13:15:22Z',
    status: 'Active',
    severity: 'Critical',
    ip_address: '45.123.78.210',
    region: 'eastus'
  },
  {
    id: 'inc-003',
    cloud: 'AWS',
    principal: 'arn:aws:iam::123456789012:role/trap-role',
    trigger_type: 'DynamoDB Query',
    timestamp: '2025-10-27T11:42:18Z',
    status: 'Resolved',
    severity: 'Medium',
    ip_address: '102.34.56.178',
    region: 'eu-west-1'
  },
  {
    id: 'inc-004',
    cloud: 'Azure',
    principal: 'honeypot-app@tenant.onmicrosoft.com',
    trigger_type: 'Storage Blob Read',
    timestamp: '2025-10-27T10:18:55Z',
    status: 'Resolved',
    severity: 'Low',
    ip_address: '78.92.145.23',
    region: 'westus2'
  },
  {
    id: 'inc-005',
    cloud: 'AWS',
    principal: 'arn:aws:iam::987654321098:user/decoy-admin',
    trigger_type: 'Lambda Invocation',
    timestamp: '2025-10-27T09:33:12Z',
    status: 'Active',
    severity: 'High',
    ip_address: '156.78.90.234',
    region: 'ap-southeast-1'
  }
];

/**
 * Mock detailed incident (for detail page)
 */
export const MOCK_INCIDENT_DETAIL = {
  id: 'inc-001',
  cloud: 'AWS',
  principal: 'arn:aws:iam::123456789012:user/honeypot-user',
  trigger_type: 'S3 Access',
  timestamp: '2025-10-27T14:23:45Z',
  status: 'Active',
  severity: 'High',
  ip_address: '203.45.67.89',
  region: 'us-east-1',
  resource_arn: 'arn:aws:s3:::honeypot-bucket-prod/sensitive-data.zip',
  user_agent: 'aws-cli/2.13.5 Python/3.11.4 Linux/5.15.0',
  response_actions: [
    {
      action: 'Credential Revoked',
      timestamp: '2025-10-27T14:24:02Z',
      status: 'Success'
    },
    {
      action: 'Security Team Notified',
      timestamp: '2025-10-27T14:24:05Z',
      status: 'Success'
    },
    {
      action: 'CloudTrail Logs Captured',
      timestamp: '2025-10-27T14:24:08Z',
      status: 'Success'
    }
  ],
  evidence: {
    cloudtrail_log: 'https://s3.amazonaws.com/evidence/inc-001-cloudtrail.json',
    vpc_flow_logs: 'https://s3.amazonaws.com/evidence/inc-001-vpc-flow.log',
    iam_snapshot: 'https://s3.amazonaws.com/evidence/inc-001-iam-snapshot.json'
  },
  timeline: [
    { event: 'Honeytoken Triggered', timestamp: '2025-10-27T14:23:45Z' },
    { event: 'Automated Response Initiated', timestamp: '2025-10-27T14:24:00Z' },
    { event: 'Evidence Collection Started', timestamp: '2025-10-27T14:24:08Z' },
    { event: 'Evidence Saved to S3', timestamp: '2025-10-27T14:24:15Z' }
  ],
  threat_indicators: {
    is_vpn: false,
    is_tor: false,
    is_known_attacker: true,
    geo_location: 'Singapore'
  }
};

/**
 * Mock time-series data for charts
 */
export const MOCK_TIMESERIES = [
  { date: '2025-10-21', count: 5 },
  { date: '2025-10-22', count: 8 },
  { date: '2025-10-23', count: 3 },
  { date: '2025-10-24', count: 12 },
  { date: '2025-10-25', count: 7 },
  { date: '2025-10-26', count: 9 },
  { date: '2025-10-27', count: 3 }
];

export default api;