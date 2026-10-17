import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  BarChart3,
  Clock3,
  Terminal,
  Network,
  Activity,
  Gauge,
  PlayCircle
} from 'lucide-react';

export default function AnalysisNavTabs({ id, activeTab }) {
  const currentId = id || '609315c9a54f4a64b733cb9ff93e5478';

  const tabs = [
    {
      to: `/results/${currentId}`,
      key: 'results',
      label: 'Results Dashboard',
      icon: BarChart3
    },
    {
      to: `/schedule/${currentId}`,
      key: 'schedule',
      label: 'Schedule View (Gantt)',
      icon: Clock3,
      highlight: true
    },
    {
      to: `/output/${currentId}`,
      key: 'output',
      label: 'Code & Standard Output (stdout)',
      icon: Terminal,
      highlight: true
    },
    {
      to: `/pairs/${currentId}`,
      key: 'pairs',
      label: 'Pair Analysis',
      icon: Network
    },
    {
      to: `/tasks/${currentId}`,
      key: 'tasks',
      label: 'Task Metrics',
      icon: Activity
    },
    {
      to: `/predictions/${currentId}`,
      key: 'predictions',
      label: 'Prediction Model',
      icon: Gauge
    },
    {
      to: `/jobs/${currentId}`,
      key: 'jobs',
      label: 'Job Telemetry',
      icon: PlayCircle
    }
  ];

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      margin: '0 0 20px 0',
      padding: '8px 12px',
      background: '#0d1522',
      border: '1px solid #1c2a3d',
      borderRadius: 10,
      overflowX: 'auto',
      boxShadow: '0 4px 14px rgba(0,0,0,0.2)'
    }}>
      <div style={{
        fontSize: 11,
        color: '#6e829c',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        paddingRight: 8,
        borderRight: '1px solid #1e2c3f',
        marginRight: 4,
        whiteSpace: 'nowrap',
        display: 'flex',
        alignItems: 'center',
        gap: 6
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4bd6d2', display: 'inline-block' }}/>
        Views:
      </div>

      {tabs.map(tab => {
        const Icon = tab.icon;
        return (
          <NavLink
            key={tab.key}
            to={tab.to}
            style={({ isActive }) => {
              const active = isActive || activeTab === tab.key;
              return {
                display: 'inline-flex',
                alignItems: 'center',
                gap: 7,
                padding: '6px 14px',
                borderRadius: 7,
                fontSize: 12.5,
                fontWeight: active ? 600 : 500,
                color: active ? '#ffffff' : '#8fa0b6',
                background: active
                  ? 'linear-gradient(135deg, rgba(75, 214, 210, 0.22) 0%, rgba(56, 189, 248, 0.15) 100%)'
                  : '#121b27',
                border: active ? '1px solid #4bd6d2' : '1px solid #1e2c3e',
                textDecoration: 'none',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
                boxShadow: active ? '0 2px 8px rgba(75, 214, 210, 0.2)' : 'none'
              };
            }}
          >
            <Icon size={14} color="#4bd6d2"/>
            <span>{tab.label}</span>
          </NavLink>
        );
      })}
    </div>
  );
}
