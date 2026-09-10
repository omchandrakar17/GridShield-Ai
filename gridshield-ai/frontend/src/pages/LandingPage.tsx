import React from 'react'
import { Link } from 'react-router-dom'
import {
  ShieldAlert, ArrowUpRight, Upload, ScanSearch, Sparkles,
  FolderOpen, FileDown, Github,
} from 'lucide-react'

// ── Static, illustrative example data used only to demonstrate the UI ──────
// This is not live data — it mirrors the shape of a real GridShield AI result.
const EXAMPLE = {
  consumerId: 'CON-84210',
  score: 82,
  level: 'Critical' as const,
  flagType: 'BILLING_MISMATCH',
  period: '2024-03',
  series: [61, 58, 64, 60, 57, 62, 24, 21, 26, 23, 25, 22],
}

const LEVEL_COLOR: Record<string, string> = {
  Critical: '#F5A623',
  High: '#F7B84D',
}

const DETECTORS = [
  { code: 'SUDDEN_DROP', desc: 'Consumption drops 40% or more in a single billing period.' },
  { code: 'SUDDEN_SPIKE', desc: 'Consumption jumps to 2.5x or more of the historical mean.' },
  { code: 'HIGH_ZSCORE', desc: 'A reading sits more than 2.5 standard deviations from the consumer\u2019s own mean.' },
  { code: 'BILLING_MISMATCH', desc: 'Billed units diverge from metered units by more than 10%.' },
  { code: 'METER_GAP', desc: 'The meter reading difference doesn\u2019t match the recorded consumption.' },
  { code: 'ZERO_CONSUMPTION', desc: 'Near-zero usage on a meter with an active history.' },
  { code: 'HIGH_VARIABILITY', desc: 'Coefficient of variation exceeds 80% across the billing history.' },
]

const AGENTS = [
  { name: 'DataAnalysisAgent', desc: 'Reads the consumption profile and summarizes what\u2019s normal for this consumer.' },
  { name: 'AnomalyDetectionAgent', desc: 'Reviews each statistical flag in context and rules out benign explanations.' },
  { name: 'FraudInvestigationAgent', desc: 'Correlates indicators into a single investigation narrative.' },
  { name: 'ExplainabilityAgent', desc: 'Turns the narrative into evidence a non-technical investigator can act on.' },
  { name: 'DecisionSupportAgent', desc: 'Assigns priority and a recommended next action.' },
]

const WORKFLOW = [
  { icon: Upload, title: 'Upload billing data', desc: 'Drop in a CSV or Excel export \u2014 columns auto-map from 50+ common naming variants.' },
  { icon: ScanSearch, title: 'Run detection', desc: 'Seven statistical detectors score every consumer. No AI keys required for this step.' },
  { icon: Sparkles, title: 'Investigate with AI', desc: 'A five-agent pipeline builds a plain-language narrative on top of the statistics.' },
  { icon: FolderOpen, title: 'Open a case', desc: 'Assign an investigator, track status, and log notes on a timeline.' },
  { icon: FileDown, title: 'Export the report', desc: 'Download a PDF or JSON report ready to hand to a field team.' },
]

function Waveform() {
  const w = 320, h = 120, pad = 12
  const max = Math.max(...EXAMPLE.series)
  const min = Math.min(...EXAMPLE.series)
  const points = EXAMPLE.series.map((v, i) => {
    const x = pad + (i * (w - pad * 2)) / (EXAMPLE.series.length - 1)
    const y = h - pad - ((v - min) / (max - min)) * (h - pad * 2)
    return [x, y]
  })
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
  const dropIndex = 6
  const dropPoint = points[dropIndex]

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto">
      <path d={path} fill="none" stroke="#2DD4BF" strokeWidth="2" />
      {points.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r={i === dropIndex ? 4 : 2}
          fill={i === dropIndex ? '#F5A623' : '#2DD4BF'} />
      ))}
      <line x1={dropPoint[0]} y1={dropPoint[1] - 30} x2={dropPoint[0]} y2={dropPoint[1] - 8}
        stroke="#F5A623" strokeWidth="1" strokeDasharray="2 2" />
      <text x={dropPoint[0]} y={dropPoint[1] - 34} textAnchor="middle" fill="#F5A623" fontSize="9"
        fontFamily="'IBM Plex Mono', monospace">
        -61% vs mean
      </text>
    </svg>
  )
}

function Gauge() {
  const r = 46, circ = 2 * Math.PI * r
  const pct = EXAMPLE.score
  const dash = (pct / 100) * circ
  const color = LEVEL_COLOR[EXAMPLE.level]
  return (
    <svg width="116" height="116" viewBox="0 0 116 116">
      <circle cx="58" cy="58" r={r} fill="none" stroke="#1E344F" strokeWidth="9" />
      <circle cx="58" cy="58" r={r} fill="none" stroke={color} strokeWidth="9"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" transform="rotate(-90 58 58)" />
      <text x="58" y="54" textAnchor="middle" fill="#fff" fontSize="26" fontWeight="600"
        fontFamily="'IBM Plex Mono', monospace">{pct}</text>
      <text x="58" y="72" textAnchor="middle" fill="#6B85A3" fontSize="9"
        fontFamily="'IBM Plex Mono', monospace">/ 100</text>
    </svg>
  )
}

export default function LandingPage() {
  return (
    <div className="landing bg-ink text-white">
      {/* ── Nav ─────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 bg-ink/90 backdrop-blur border-b border-ink-600">
        <div className="landing-section flex items-center justify-between h-16">
          <div className="flex items-center gap-2.5">
            <div className="bg-amber rounded-md p-1.5">
              <ShieldAlert className="w-4 h-4 text-ink" />
            </div>
            <span className="font-semibold tracking-tight">GridShield AI</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm text-ink-300">
            <a href="#workflow" className="hover:text-white transition-colors">How it works</a>
            <a href="#capabilities" className="hover:text-white transition-colors">Detection</a>
            <a href="#agents" className="hover:text-white transition-colors">AI agents</a>
          </nav>
          <Link to="/dashboard" className="landing-btn-primary !px-4 !py-2">
            Launch dashboard
          </Link>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="landing-section pt-16 pb-20 lg:pt-24 lg:pb-28 grid lg:grid-cols-2 gap-14 items-center">
        <div>
          <h1 className="text-4xl lg:text-[3.25rem] leading-[1.08] font-semibold tracking-tight">
            See electricity theft before the meter does.
          </h1>
          <p className="mt-6 text-lg text-ink-300 max-w-lg leading-relaxed">
            GridShield AI turns raw billing and meter data into ranked, explainable fraud
            investigations. Statistical detection runs first and stands on its own; a
            five-agent AI pipeline adds the narrative on top.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link to="/dashboard" className="landing-btn-primary">
              Launch dashboard
              <ArrowUpRight className="w-4 h-4" />
            </Link>
            <a href="#workflow" className="landing-btn-secondary">
              See how it works
            </a>
          </div>
          <p className="mt-8 text-xs text-ink-300 max-w-md leading-relaxed">
            Risk scores are labeled as AI-assisted investigation priority and are not a
            legal determination of fraud.
          </p>
        </div>

        <div className="bg-ink-800 border border-ink-600 rounded-xl p-6">
          <div className="flex items-center justify-between text-xs text-ink-300 mono">
            <span>{EXAMPLE.consumerId}</span>
            <span>period {EXAMPLE.period}</span>
          </div>
          <div className="mt-4 flex items-center gap-6">
            <Gauge />
            <div>
              <div className="text-amber text-sm font-semibold">{EXAMPLE.level} risk</div>
              <div className="mt-1 text-ink-300 text-xs mono">{EXAMPLE.flagType}</div>
              <div className="mt-3 text-sm text-ink-300 max-w-[180px] leading-snug">
                Consumption fell sharply while billed units stayed level.
              </div>
            </div>
          </div>
          <div className="mt-6 pt-5 border-t border-ink-600">
            <div className="text-xs text-ink-300 mb-2">12-month consumption (kWh)</div>
            <Waveform />
          </div>
          <p className="mt-3 text-[11px] text-ink-400">Illustrative example, not live data.</p>
        </div>
      </section>

      {/* ── Stat strip ──────────────────────────────────────────────────── */}
      <section className="border-y border-ink-600 bg-ink-800">
        <div className="landing-section grid grid-cols-2 md:grid-cols-4 divide-x divide-ink-600">
          {[
            ['7', 'statistical detectors'],
            ['5', 'agents in the AI pipeline'],
            ['0\u2013100', 'explainable risk score'],
            ['0', 'AI keys required to start'],
          ].map(([n, label]) => (
            <div key={label} className="px-6 py-8 first:pl-0">
              <div className="text-3xl font-semibold mono text-current-400">{n}</div>
              <div className="mt-1 text-sm text-ink-300">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Workflow ────────────────────────────────────────────────────── */}
      <section id="workflow" className="landing-section py-20 lg:py-28">
        <h2 className="text-2xl lg:text-3xl font-semibold tracking-tight max-w-xl">
          From raw CSV to a field-ready case
        </h2>
        <p className="mt-3 text-ink-300 max-w-xl">
          Five steps, the same order every time — each one usable on its own from the API.
        </p>
        <ol className="mt-12 grid md:grid-cols-5 gap-8">
          {WORKFLOW.map((step, i) => (
            <li key={step.title} className="relative">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full border border-current-500 flex items-center justify-center text-current-400 mono text-sm shrink-0">
                  {i + 1}
                </div>
                {i < WORKFLOW.length - 1 && (
                  <div className="hidden md:block h-px flex-1 bg-ink-600" />
                )}
              </div>
              <step.icon className="w-5 h-5 text-amber mt-5" />
              <h3 className="mt-3 font-medium">{step.title}</h3>
              <p className="mt-2 text-sm text-ink-300 leading-relaxed">{step.desc}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ── Detection capabilities ──────────────────────────────────────── */}
      <section id="capabilities" className="border-t border-ink-600 bg-ink-800">
        <div className="landing-section py-20 lg:py-28 grid lg:grid-cols-[280px_1fr] gap-12">
          <div>
            <h2 className="text-2xl lg:text-3xl font-semibold tracking-tight">
              Seven detectors, no hidden thresholds
            </h2>
            <p className="mt-3 text-ink-300 text-sm leading-relaxed">
              Every threshold is a configurable environment variable, not a black box.
              Statistical detection runs the same way whether or not AI narratives are enabled.
            </p>
          </div>
          <div className="divide-y divide-ink-600 border-t border-b border-ink-600">
            {DETECTORS.map((d) => (
              <div key={d.code} className="py-4 grid sm:grid-cols-[220px_1fr] gap-2 sm:gap-6">
                <div className="mono text-sm text-amber">{d.code}</div>
                <div className="text-sm text-ink-300">{d.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Agent pipeline ──────────────────────────────────────────────── */}
      <section id="agents" className="landing-section py-20 lg:py-28">
        <h2 className="text-2xl lg:text-3xl font-semibold tracking-tight max-w-xl">
          A five-agent pipeline, each step building on the last
        </h2>
        <p className="mt-3 text-ink-300 max-w-xl">
          Powered by IBM watsonx.ai. If no credentials are configured, every agent still
          runs and returns a clearly labeled statistical summary instead of a narrative.
        </p>
        <div className="mt-12 space-y-0">
          {AGENTS.map((agent, i) => (
            <div key={agent.name} className="flex gap-6 py-5 border-t border-ink-600 last:border-b">
              <div className="mono text-sm text-ink-400 w-6 pt-0.5 shrink-0">{i + 1}</div>
              <div className="w-56 shrink-0 font-medium mono text-sm text-current-400">{agent.name}</div>
              <div className="text-sm text-ink-300 leading-relaxed">{agent.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────────────── */}
      <section className="border-t border-ink-600 bg-ink-800">
        <div className="landing-section py-20 text-center">
          <h2 className="text-2xl lg:text-3xl font-semibold tracking-tight">
            Upload a dataset and see the risk scores in minutes
          </h2>
          <p className="mt-3 text-ink-300 max-w-lg mx-auto">
            Works with your own billing export, or a generated sample dataset for testing.
          </p>
          <div className="mt-8 flex justify-center">
            <Link to="/dashboard" className="landing-btn-primary">
              Launch dashboard
              <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-ink-600">
        <div className="landing-section py-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-ink-300">
            <ShieldAlert className="w-4 h-4" />
            GridShield AI — agentic fraud detection & investigation platform
          </div>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-sm text-ink-300 hover:text-white transition-colors"
          >
            <Github className="w-4 h-4" />
            API reference
          </a>
        </div>
        <div className="landing-section pb-10 text-[11px] text-ink-400 max-w-2xl">
          GridShield AI is an investigative support tool. All fraud risk scores and AI
          assessments are labeled as AI-assisted investigation priority and do not
          constitute a legal determination of fraud.
        </div>
      </footer>
    </div>
  )
}
