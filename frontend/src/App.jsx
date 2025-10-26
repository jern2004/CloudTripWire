import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import IncidentDetailPage from './pages/IncidentDetailPage';

/**
 * App - Root application component with routing
 */
function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incident/:id" element={<IncidentDetailPage />} />
          {/* Add more routes as needed */}
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;