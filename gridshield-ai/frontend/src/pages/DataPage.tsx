import React, { useEffect, useState, useRef } from 'react'
import { uploadDataset, getDatasetStats, getAgentStatus } from '../services/api'
import { PageHeader, LoadingSpinner, ErrorState } from '../components/shared'
import { Upload, Database, CheckCircle, AlertTriangle, Zap, ExternalLink } from 'lucide-react'

export default function DataPage() {
  const [datasetStats, setDatasetStats] = useState<any>(null)
  const [agentStatus, setAgentStatus] = useState<any>(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState<any>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchStats = async () => {
    setStatsLoading(true)
    try {
      const [s, a] = await Promise.all([getDatasetStats(), getAgentStatus()])
      setDatasetStats(s.data)
      setAgentStatus(a.data)
    } catch { } finally {
      setStatsLoading(false)
    }
  }

  useEffect(() => { fetchStats() }, [])

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadResult(null)
    setUploadError(null)
    setUploadProgress(0)
    try {
      const res = await uploadDataset(file, pct => setUploadProgress(pct))
      setUploadResult(res.data)
      fetchStats()
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail ?? 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div>
      <PageHeader
        title="Data Management"
        subtitle="Ingest electricity billing data and configure IBM watsonx.ai"
      />

      <div className="p-6 space-y-6">
        {/* Dataset info */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Database className="w-4 h-4" /> Current Dataset
          </h3>
          {statsLoading ? (
            <LoadingSpinner message="Loading stats…" />
          ) : datasetStats ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              {[
                ['Total Consumers', datasetStats.total_consumers?.toLocaleString() ?? '0'],
                ['Total Records', datasetStats.total_records?.toLocaleString() ?? '0'],
                ['Earliest Period', datasetStats.earliest_period ?? '—'],
                ['Latest Period', datasetStats.latest_period ?? '—'],
                ['Avg Consumption', datasetStats.avg_consumption ? `${Number(datasetStats.avg_consumption).toFixed(1)} kWh` : '—'],
                ['Source Files', datasetStats.source_files ?? '0'],
              ].map(([l, v]) => (
                <div key={String(l)} className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs text-gray-400">{l}</div>
                  <div className="font-semibold text-gray-900 mt-0.5">{String(v)}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No data loaded yet.</p>
          )}
        </div>

        {/* Upload */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <Upload className="w-4 h-4" /> Upload Billing Dataset
          </h3>
          <p className="text-xs text-gray-500 mb-4">
            Accepts CSV or Excel files. Columns are auto-mapped from common real-world billing data formats.
            Required: a consumer/account ID column. Supported: billing period, meter readings, units consumed,
            billed units, amount billed, tariff category, consumer type, location, division.
          </p>

          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 cursor-pointer transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-600 font-medium">Click to select a CSV or Excel file</p>
            <p className="text-xs text-gray-400 mt-1">
              Max recommended: 100MB · CSV (.csv, .txt) or Excel (.xlsx, .xls)
            </p>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".csv,.txt,.xlsx,.xls"
              onChange={handleFileChange}
            />
          </div>

          {uploading && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                <span>Uploading and validating…</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="h-2 bg-blue-500 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          )}

          {uploadResult && (
            <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-green-800">Upload Successful</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs mb-3">
                {[
                  ['Original Rows', uploadResult.report?.original_rows],
                  ['Inserted', uploadResult.report?.inserted_rows],
                  ['Skipped (dup)', uploadResult.report?.skipped_duplicate_rows],
                  ['Final Rows', uploadResult.report?.final_rows],
                ].map(([l, v]) => (
                  <div key={String(l)} className="bg-ink-700 rounded p-2">
                    <div className="text-gray-400">{l}</div>
                    <div className="font-semibold text-gray-900">{v ?? '—'}</div>
                  </div>
                ))}
              </div>
              {uploadResult.report?.canonical_fields_present?.length > 0 && (
                <div className="text-xs text-green-700 mb-2">
                  <strong>Mapped fields:</strong> {uploadResult.report.canonical_fields_present.join(', ')}
                </div>
              )}
              {uploadResult.report?.issues?.length > 0 && (
                <details className="text-xs">
                  <summary className="text-orange-600 cursor-pointer">
                    {uploadResult.report.issues.length} validation note{uploadResult.report.issues.length !== 1 ? 's' : ''}
                  </summary>
                  <ul className="mt-1 space-y-0.5 text-orange-700">
                    {uploadResult.report.issues.map((issue: string, i: number) => (
                      <li key={i}>• {issue}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}

          {uploadError && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{uploadError}</p>
            </div>
          )}
        </div>

        {/* IBM watsonx.ai status */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4" /> IBM watsonx.ai Agent Status
          </h3>
          {agentStatus ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${agentStatus.watsonx_configured ? 'bg-green-500' : 'bg-orange-400'}`} />
                <span className="text-sm font-medium">
                  {agentStatus.watsonx_configured ? 'IBM watsonx.ai connected' : 'IBM watsonx.ai not configured'}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                Model: <code className="bg-gray-100 px-1 rounded">{agentStatus.model_id}</code>
              </div>
              {!agentStatus.watsonx_configured && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <p className="text-sm text-orange-800 font-medium mb-2">Configure IBM watsonx.ai for AI narratives</p>
                  <p className="text-xs text-orange-700 mb-3">{agentStatus.note}</p>
                  <div className="text-xs space-y-1 text-orange-700">
                    <p className="font-medium">Required environment variables (set in backend/.env):</p>
                    {agentStatus.required_env_vars?.map((v: string) => (
                      <code key={v} className="block bg-orange-100 px-2 py-0.5 rounded font-mono">{v}=your_value</code>
                    ))}
                  </div>
                  <a
                    href="https://cloud.ibm.com/catalog/services/watson-machine-learning"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mt-3"
                  >
                    Get IBM Cloud credentials <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-xs text-blue-700">
                  <strong>Note:</strong> Statistical anomaly detection runs fully without IBM watsonx.ai.
                  AI narrative generation (agent reasoning text) requires a valid IBM Cloud API key and project ID.
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">Could not reach backend agent status endpoint.</p>
          )}
        </div>

        {/* Real dataset guidance */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Real Dataset Sources</h3>
          <p className="text-xs text-gray-500 mb-4">
            For production use, replace the sample dataset with real electricity billing data from:
          </p>
          <div className="space-y-3">
            {[
              {
                name: 'SGCC Electricity Theft Dataset (Kaggle)',
                desc: 'State Grid Corporation of China electricity theft detection dataset. Contains labeled fraud/normal consumption data.',
                url: 'https://www.kaggle.com/datasets/dvnguyen/electricity-theft-detection',
              },
              {
                name: 'UCI Household Electric Power Consumption',
                desc: 'Individual household electric power consumption measurements over 4 years at 1-minute resolution.',
                url: 'https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption',
              },
              {
                name: 'Your Utility / Open Government Data Portal',
                desc: 'Many countries publish electricity billing data through open data portals (data.gov, data.gov.in, etc.).',
                url: 'https://data.gov',
              },
            ].map(source => (
              <div key={source.name} className="border border-gray-200 rounded-lg p-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{source.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{source.desc}</p>
                  </div>
                  <a
                    href={source.url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline flex items-center gap-1 shrink-0"
                  >
                    Visit <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs text-gray-500">
            <strong>For quick testing:</strong> Generate a sample dataset by running{' '}
            <code className="bg-gray-100 px-1 rounded">python data/generate_sample.py</code> from the project root,
            then upload the generated <code className="bg-gray-100 px-1 rounded">data/sample/sample_billing_data.csv</code> file above.
            This sample data is clearly labeled and must not be used in production.
          </div>
        </div>
      </div>
    </div>
  )
}
