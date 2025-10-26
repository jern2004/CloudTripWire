import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

/**
 * MetricCard - Reusable card component for displaying key metrics
 * 
 * @param {Object} props
 * @param {string} props.title - Card title
 * @param {number|string} props.value - Main metric value
 * @param {React.Component} props.icon - Lucide icon component
 * @param {string} props.color - Accent color (blue, red, green, yellow)
 * @param {Object} props.change - Optional change indicator {percent, direction}
 */
const MetricCard = ({ title, value, icon: Icon, color = 'blue', change }) => {
  // Color mapping for different metric types
  const colorClasses = {
    blue: 'from-blue-500/20 to-blue-600/20 border-blue-500/50',
    red: 'from-red-500/20 to-red-600/20 border-red-500/50',
    green: 'from-green-500/20 to-green-600/20 border-green-500/50',
    yellow: 'from-yellow-500/20 to-yellow-600/20 border-yellow-500/50',
    orange: 'from-orange-500/20 to-orange-600/20 border-orange-500/50',
  };

  const iconColorClasses = {
    blue: 'text-blue-400',
    red: 'text-red-400',
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    orange: 'text-orange-400',
  };

  // Render trend indicator
  const renderTrendIcon = () => {
    if (!change) return null;
    
    const { percent, direction } = change;
    
    if (direction === 'up') {
      return (
        <div className="flex items-center text-green-400 text-sm mt-2">
          <TrendingUp className="w-4 h-4 mr-1" />
          <span>+{percent}%</span>
        </div>
      );
    } else if (direction === 'down') {
      return (
        <div className="flex items-center text-red-400 text-sm mt-2">
          <TrendingDown className="w-4 h-4 mr-1" />
          <span>-{percent}%</span>
        </div>
      );
    } else {
      return (
        <div className="flex items-center text-gray-400 text-sm mt-2">
          <Minus className="w-4 h-4 mr-1" />
          <span>No change</span>
        </div>
      );
    }
  };

  return (
    <div 
      className={`
        relative overflow-hidden
        bg-gradient-to-br ${colorClasses[color]}
        border ${colorClasses[color].split(' ')[2]}
        rounded-xl p-6
        card-hover animate-fade-in
      `}
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full blur-3xl -mr-16 -mt-16" />
      
      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-dark-muted text-sm font-medium uppercase tracking-wide">
            {title}
          </h3>
          {Icon && <Icon className={`w-6 h-6 ${iconColorClasses[color]}`} />}
        </div>
        
        <div className="flex items-baseline">
          <p className="text-4xl font-bold text-dark-text">
            {value}
          </p>
        </div>
        
        {renderTrendIcon()}
      </div>
    </div>
  );
};

export default MetricCard;