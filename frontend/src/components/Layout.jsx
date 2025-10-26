import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  AlertTriangle, 
  Shield,
  Menu,
  X,
  Github,
  Settings
} from 'lucide-react';

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/incidents', label: 'All Incidents', icon: AlertTriangle },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-dark-bg">
      <nav className="bg-dark-surface border-b border-dark-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden mr-4 p-2 rounded-lg hover:bg-dark-bg transition-colors"
              >
                {sidebarOpen ? (
                  <X className="w-6 h-6 text-dark-text" />
                ) : (
                  <Menu className="w-6 h-6 text-dark-text" />
                )}
              </button>
              
              <Link to="/" className="flex items-center space-x-3">
                <div className="bg-gradient-to-br from-accent-primary to-accent-secondary p-2 rounded-lg">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-dark-text">CloudTripwire</h1>
                  <p className="text-xs text-dark-muted">Honeytoken Security Monitor</p>
                </div>
              </Link>
            </div>

            <div className="hidden lg:flex items-center space-x-4">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`
                    flex items-center px-4 py-2 rounded-lg transition-colors
                    ${isActive(item.path)
                      ? 'bg-accent-primary/20 text-accent-primary'
                      : 'text-dark-muted hover:text-dark-text hover:bg-dark-bg'
                    }
                  `}
                >
                  <item.icon className="w-4 h-4 mr-2" />
                  {item.label}
                </Link>
              ))}
            </div>

            <div className="flex items-center space-x-2">
              <a
                href="https://github.com/jern2004/CloudTripWire"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg hover:bg-dark-bg transition-colors"
              >
                <Github className="w-5 h-5 text-dark-muted hover:text-dark-text" />
              </a>
              <button className="p-2 rounded-lg hover:bg-dark-bg transition-colors">
                <Settings className="w-5 h-5 text-dark-muted hover:text-dark-text" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/50 z-40" onClick={() => setSidebarOpen(false)} />
      )}

      <aside
        className={`
          lg:hidden fixed top-16 left-0 bottom-0 w-64 bg-dark-surface border-r border-dark-border z-40
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="p-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setSidebarOpen(false)}
              className={`
                flex items-center px-4 py-3 rounded-lg transition-colors
                ${isActive(item.path)
                  ? 'bg-accent-primary/20 text-accent-primary'
                  : 'text-dark-muted hover:text-dark-text hover:bg-dark-bg'
                }
              `}
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.label}
            </Link>
          ))}
        </div>
      </aside>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      <footer className="bg-dark-surface border-t border-dark-border mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <p className="text-dark-muted text-sm">
              © 2025 CloudTripwire. Multi-Cloud Honeytokens & Auto-Incident Response.
            </p>
            <div className="flex items-center space-x-4 mt-4 md:mt-0">
              <a href="#" className="text-dark-muted hover:text-dark-text text-sm transition-colors">Documentation</a>
              <a href="#" className="text-dark-muted hover:text-dark-text text-sm transition-colors">API</a>
              <a href="#" className="text-dark-muted hover:text-dark-text text-sm transition-colors">Support</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
