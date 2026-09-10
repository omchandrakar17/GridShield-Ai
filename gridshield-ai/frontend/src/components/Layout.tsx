import React from 'react'
import { NavLink, Link } from 'react-router-dom'
import {
  LayoutDashboard, Search, FolderOpen, AlertTriangle,
  Database, ShieldAlert, Zap, ArrowLeft
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard',  label: 'Dashboard',       icon: LayoutDashboard },
  { to: '/investigate',label: 'Investigate',      icon: Search },
  { to: '/anomalies',  label: 'Anomalies',        icon: AlertTriangle },
  { to: '/cases',      label: 'Cases',            icon: FolderOpen },
  { to: '/data',       label: 'Data Management',  icon: Database },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-ink flex flex-col shrink-0">
        {/* Brand */}
        <Link to="/" className="px-6 py-5 border-b border-ink-600 flex items-center gap-2.5 hover:bg-ink-800 transition-colors">
          <div className="bg-amber rounded-lg p-1.5">
            <ShieldAlert className="w-5 h-5 text-ink" />
          </div>
          <div>
            <div className="text-white font-semibold text-base leading-tight">GridShield AI</div>
            <div className="text-ink-300 text-[10px] uppercase tracking-wider">Fraud Detection</div>
          </div>
        </Link>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-ink-600 text-white border-l-2 border-amber -ml-0.5 pl-[11px]'
                    : 'text-ink-300 hover:bg-ink-700 hover:text-white'
                )
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Back to site + IBM badge */}
        <div className="px-4 py-4 border-t border-ink-600 space-y-3">
          <Link to="/" className="flex items-center gap-2 text-ink-300 hover:text-white text-xs transition-colors">
            <ArrowLeft className="w-3 h-3" />
            Back to overview
          </Link>
          <div className="flex items-center gap-2 text-ink-300 text-xs">
            <Zap className="w-3 h-3 text-amber" />
            Powered by IBM watsonx.ai
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="min-h-full">
          {children}
        </div>
      </main>
    </div>
  )
}
