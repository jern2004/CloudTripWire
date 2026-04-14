import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import IncidentsPage from './pages/IncidentsPage';
import IncidentDetailPage from './pages/IncidentDetailPage';

/**
 * App - Root application component with routing
 */
function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/"             element={<Dashboard />} />
          <Route path="/incidents"    element={<IncidentsPage />} />
          <Route path="/incident/:id" element={<IncidentDetailPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;