'use client';

import { useState, useEffect } from 'react';
import { Activity, Github, BookOpen, Zap } from 'lucide-react';
import { getBasicHealth } from '@/lib/api';

export default function Header() {
  const [health, setHealth] = useState<'healthy' | 'degraded' | 'unhealthy' | 'loading'>('loading');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await getBasicHealth();
        setHealth(data.status === 'healthy' ? 'healthy' : 'degraded');
      } catch {
        setHealth('unhealthy');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const statusColors = {
    healthy: 'bg-emerald-500',
    degraded: 'bg-amber-500',
    unhealthy: 'bg-red-500',
    loading: 'bg-gray-400 animate-pulse',
  };

  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-lg shadow-primary-500/25">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">
                LLM Orchestration Engine
              </h1>
              <p className="text-xs text-slate-500 hidden sm:block">
                Intelligent Multi-Model Routing
              </p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex items-center gap-6">
            {/* Status Indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-full">
              <span className={`w-2 h-2 rounded-full ${statusColors[health]}`} />
              <span className="text-sm font-medium text-slate-600 capitalize">
                {health === 'loading' ? 'Checking...' : health}
              </span>
            </div>

            {/* Links */}
            <div className="hidden md:flex items-center gap-4">
              <a
                href="/docs"
                className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-primary-600 transition-colors"
              >
                <BookOpen className="w-4 h-4" />
                <span>API Docs</span>
              </a>
              <a
                href="https://github.com/yourusername/llm-orchestration-engine"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-primary-600 transition-colors"
              >
                <Github className="w-4 h-4" />
                <span>GitHub</span>
              </a>
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}