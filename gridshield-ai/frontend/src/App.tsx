import React from 'react'
import { Routes, Route, Outlet } from 'react-router-dom'
import Layout from './components/Layout'
import LandingPage from './pages/LandingPage'
import DashboardPage from './pages/DashboardPage'
import InvestigatePage from './pages/InvestigatePage'
import CasesPage from './pages/CasesPage'
import CaseDetailPage from './pages/CaseDetailPage'
import DataPage from './pages/DataPage'
import AnomalyListPage from './pages/AnomalyListPage'

function AppShell() {
  return (
    <Layout>
      <Outlet />
    </Layout>
  )
}

export default function App() {
  return (
    <Routes>
      {/* Public marketing page — no sidebar */}
      <Route path="/" element={<LandingPage />} />

      {/* App routes — wrapped in the sidebar shell */}
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/investigate" element={<InvestigatePage />} />
        <Route path="/investigate/:consumerId" element={<InvestigatePage />} />
        <Route path="/cases" element={<CasesPage />} />
        <Route path="/cases/:caseId" element={<CaseDetailPage />} />
        <Route path="/anomalies" element={<AnomalyListPage />} />
        <Route path="/data" element={<DataPage />} />
      </Route>
    </Routes>
  )
}
