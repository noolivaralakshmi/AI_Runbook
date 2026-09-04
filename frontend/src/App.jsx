import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Inbox, Database, Settings, Zap, AlertTriangle,
  CheckCircle, Clock, XCircle, GitBranch, Ticket, Bot, ExternalLink,
  MessageSquare, ArrowLeft, ChevronRight, Server, HardDrive, Cpu, RefreshCw, Terminal
} from 'lucide-react'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

/* ─── Status & Severity Badges ─── */
function StatusBadge({ status }) {
  const styles = {
    done: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    resolved: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    running: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    active: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    failed: 'bg-red-500/20 text-red-300 border-red-500/30',
    pending: 'bg-white/5 text-white/40 border-white/10',
    intake: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    diagnosing: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    remediating: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    executing: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  }
  return (
    <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded border ${styles[status] || styles.pending}`}>
      {status}
    </span>
  )
}

function SeverityBadge({ severity }) {
  const styles = {
    low: 'bg-green-500/20 text-green-300',
    medium: 'bg-yellow-500/20 text-yellow-300',
    high: 'bg-orange-500/20 text-orange-300',
    critical: 'bg-red-500/20 text-red-300',
  }
  return (
    <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded ${styles[severity] || styles.medium}`}>
      {severity}
    </span>
  )
}

/* ─── Pipeline Step Card ─── */
function PipelineStepCard({ step, number }) {
  const statusColors = {
    done: 'border-emerald-500/30 bg-dark-800',
    running: 'border-yellow-500/30 bg-dark-800 animate-pulse',
    pending: 'border-white/5 bg-dark-900/50',
    failed: 'border-red-500/30 bg-dark-800',
  }
  const numberColors = {
    done: 'bg-emerald-500/20 text-emerald-300',
    running: 'bg-yellow-500/20 text-yellow-300',
    pending: 'bg-white/5 text-white/20',
    failed: 'bg-red-500/20 text-red-300',
  }
  const labels = {
    intake: { name: 'Discord / Manual Intake', desc: 'Bridge complaint' },
    diagnosis: { name: 'Diagnostician', desc: 'Evidence + hypotheses' },
    remediation: { name: 'Remediator', desc: 'Safe proposal' },
    execution: { name: 'Connector Writes', desc: 'GitHub Issues + PRs' },
    memory: { name: 'Memory Store', desc: 'Final incident ID' },
  }
  const label = labels[step.step_name] || { name: step.step_name, desc: '' }
  const badgeLabel = step.status === 'done' ? 'DONE' : step.status === 'running' ? 'ACTIVE' : step.status === 'failed' ? 'FAILED' : 'PENDING'

  return (
    <div className={`flex-1 min-w-[160px] rounded-xl border p-4 ${statusColors[step.status]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold ${numberColors[step.status]}`}>
          {number}
        </span>
        <StatusBadge status={badgeLabel.toLowerCase()} />
      </div>
      <p className={`text-sm font-medium ${step.status === 'pending' ? 'text-white/30' : 'text-white/90'}`}>
        {label.name}
      </p>
      <p className={`text-xs mt-0.5 ${step.status === 'pending' ? 'text-white/15' : 'text-white/40'}`}>
        {label.desc}
      </p>
    </div>
  )
}

/* ─── Connector Target Row ─── */
function ConnectorTarget({ icon, name, action, status, url }) {
  const statusStyles = {
    succeeded: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    created: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    running: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    awaiting: 'bg-white/10 text-white/40 border-white/10',
    failed: 'bg-red-500/20 text-red-300 border-red-500/30',
  }
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
          {icon}
        </div>
        <div>
          <p className="text-sm text-white/80 font-medium">{name}</p>
          <p className="text-xs text-white/40">{action}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded border ${statusStyles[status] || statusStyles.awaiting}`}>
          {status}
        </span>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="text-white/40 hover:text-white/70 transition-colors">
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>
    </div>
  )
}

/* ─── Activity Event Row ─── */
function ActivityEvent({ activity }) {
  const icons = {
    github: <GitBranch className="w-4 h-4 text-purple-400" />,
    discord: <MessageSquare className="w-4 h-4 text-blue-400" />,
    aws: <Server className="w-4 h-4 text-orange-400" />,
  }
  const actionLabels = {
    issueCreate: 'Creating GitHub Issue',
    draftPullRequest: 'Opening GitHub Pull Request',
    'chat.postMessage': 'Posting Discord message',
    restart_instance: 'Restarting EC2 Instance',
    restart_service: 'Restarting Service',
    cleanup_disk: 'Running Disk Cleanup',
    scale_up: 'Scaling Up Auto Scaling Group',
    config_change: 'Updating Configuration',
    run_command: 'Running SSM Command',
  }
  const statusStyles = {
    succeeded: 'bg-emerald-500/20 text-emerald-300',
    failed: 'bg-red-500/20 text-red-300',
    running: 'bg-yellow-500/20 text-yellow-300',
    pending: 'bg-orange-500/20 text-orange-300',
  }

  return (
    <div className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-xl">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
          {icons[activity.connector] || <Zap className="w-4 h-4 text-white/40" />}
        </div>
        <div>
          <p className="text-sm text-white/80 font-medium">{actionLabels[activity.action] || activity.action}</p>
          <p className="text-xs text-white/40">{activity.action}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded ${statusStyles[activity.status] || statusStyles.pending}`}>
          {activity.status}
        </span>
      </div>
    </div>
  )
}

/* ─── Incident Detail View ─── */
function IncidentDetail({ incident, onBack }) {
  if (!incident) return null
  const diagnosis = incident.diagnosis || {}
  const remediation = incident.remediation || {}
  const ticket = incident.ticket || {}
  const pr = incident.pull_request || {}
  const pipeline = incident.pipeline || []
  const activity = incident.activity || []

  const actionType = remediation.action_type || 'code_fix'
  const actionTypeConfigs = {
    code_fix: { icon: <GitBranch className="w-4 h-4 text-purple-400" />, label: 'GitHub Pull Request', color: 'purple' },
    restart_instance: { icon: <RefreshCw className="w-4 h-4 text-orange-400" />, label: 'EC2 Restart', color: 'orange' },
    restart_service: { icon: <RefreshCw className="w-4 h-4 text-yellow-400" />, label: 'Service Restart', color: 'yellow' },
    cleanup_disk: { icon: <HardDrive className="w-4 h-4 text-blue-400" />, label: 'Disk Cleanup', color: 'blue' },
    scale_up: { icon: <Cpu className="w-4 h-4 text-red-400" />, label: 'Scale Up (ASG)', color: 'red' },
    config_change: { icon: <Settings className="w-4 h-4 text-cyan-400" />, label: 'Config Change', color: 'cyan' },
    run_command: { icon: <Terminal className="w-4 h-4 text-green-400" />, label: 'Run Command (SSM)', color: 'green' },
  }
  const actionTypeConfig = actionTypeConfigs[actionType] || actionTypeConfigs.code_fix

  const isActive = ['intake', 'diagnosing', 'remediating', 'executing'].includes(incident.status)

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white/90">Dashboard</h1>
          <p className="text-xs text-white/40">Runbook Incident Command</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-emerald-400 animate-pulse' : incident.status === 'resolved' ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
          <span className="text-xs text-white/50">Pipeline {isActive ? 'active' : incident.status}</span>
        </div>
      </div>

      {/* Back button + incident title */}
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-sm text-white/40 hover:text-white/70 flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <span className="text-white/20">|</span>
        <h2 className="text-sm font-medium text-white/70">{incident.title || 'Incident'}</h2>
        <SeverityBadge severity={incident.severity} />
      </div>

      {/* Bridge Auto Execute Banner */}
      <div className="bg-gradient-to-r from-red-900/40 via-red-800/30 to-red-900/40 border border-red-500/20 rounded-xl px-5 py-3 flex items-center justify-center gap-3">
        <Zap className="w-4 h-4 text-red-400" />
        <span className="text-xs font-bold uppercase tracking-widest text-red-300">BRIDGE AUTO EXECUTE</span>
        <span className="text-xs text-white/50">Action: </span>
        <span className="text-xs font-bold text-white/80 flex items-center gap-1.5">
          {actionTypeConfig.icon}
          {actionType.replace('_', ' ')}
        </span>
      </div>

      {/* Pipeline Steps */}
      <div className="flex gap-3 overflow-x-auto pb-2">
        {pipeline.map((step, i) => (
          <PipelineStepCard key={step.id} step={step} number={i + 1} />
        ))}
      </div>

      {/* Evidence Brief + Connector Targets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Evidence Brief */}
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white/80">Evidence brief</h3>
              <p className="text-xs text-white/40">Bridge report plus grounded evidence</p>
            </div>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded bg-white/5 text-white/50 border border-white/10">
              {diagnosis.evidence ? `${diagnosis.evidence.length} sources` : '0 sources'}
            </span>
          </div>
          <div className="space-y-2">
            {diagnosis.summary && (
              <p className="text-sm text-white/60 leading-relaxed">{diagnosis.summary}</p>
            )}
            {diagnosis.confidence && (
              <p className="text-xs text-white/40 mt-2">{diagnosis.confidence}% confidence · {diagnosis.evidence?.length || 0} evidence records</p>
            )}
            {diagnosis.root_cause && (
              <div className="mt-3 p-3 bg-white/[0.03] rounded-lg border border-white/5">
                <p className="text-xs text-white/40 mb-1">Root Cause:</p>
                <p className="text-xs text-white/60">{diagnosis.root_cause}</p>
              </div>
            )}
            {diagnosis.similar_to_past && diagnosis.past_incident_match && (
              <div className="mt-3 p-3 bg-yellow-500/[0.05] rounded-lg border border-yellow-500/10">
                <div className="flex items-center gap-2 mb-1">
                  <Database className="w-3 h-3 text-yellow-400" />
                  <p className="text-xs font-semibold text-yellow-300">Memory Match Found</p>
                </div>
                <p className="text-xs text-white/60">{diagnosis.past_incident_match}</p>
              </div>
            )}
            {diagnosis.evidence && diagnosis.evidence.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-white/40 mb-2">Evidence:</p>
                <div className="space-y-1.5">
                  {diagnosis.evidence.map((e, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-white/50 p-2 bg-white/[0.02] rounded-lg border border-white/5">
                      <span className="text-emerald-400 mt-0.5">●</span>
                      <span>{e}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Connector Targets */}
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white/80">Connector targets</h3>
              <p className="text-xs text-white/40">Completion shown from connector reports</p>
            </div>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
              LIVE TARGETS
            </span>
          </div>
          <div>
            <ConnectorTarget
              icon={<Ticket className="w-4 h-4 text-blue-400" />}
              name="GitHub Issues"
              action="issueCreate"
              status={ticket.url ? 'created' : ticket.error ? 'failed' : 'awaiting'}
              url={ticket.url}
            />
            {actionType === 'code_fix' ? (
              <ConnectorTarget
                icon={<GitBranch className="w-4 h-4 text-purple-400" />}
                name="GitHub Pull Request"
                action="draftPullRequest"
                status={pr.url ? 'created' : pr.error ? 'failed' : 'awaiting'}
                url={pr.url}
              />
            ) : (
              <ConnectorTarget
                icon={actionTypeConfig.icon}
                name={actionTypeConfig.label}
                action={actionType}
                status={pr.aws_result?.success ? 'succeeded' : pr.aws_result ? 'failed' : 'awaiting'}
              />
            )}
            <ConnectorTarget
              icon={<MessageSquare className="w-4 h-4 text-blue-300" />}
              name="Discord Connector"
              action="chat.postMessage"
              status={incident.status === 'resolved' ? 'succeeded' : 'awaiting'}
            />
          </div>
        </div>
      </div>

      {/* Remediation */}
      {remediation.suggested_fix && (
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-emerald-300 mb-3">Remediation Plan</h3>
          <p className="text-sm text-white/60 mb-3">{remediation.suggested_fix}</p>
          {remediation.immediate_actions && (
            <div>
              <p className="text-xs text-white/40 mb-2">Immediate Actions:</p>
              <div className="space-y-1.5">
                {remediation.immediate_actions.map((a, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-white/55">
                    <span className="text-emerald-400 font-mono text-[10px] mt-0.5">{i + 1}.</span>
                    <span>{a}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {remediation.code_suggestion && (
            <pre className="mt-4 p-3 bg-black/40 rounded-lg text-xs text-emerald-200 overflow-x-auto border border-emerald-500/10">
              {remediation.code_suggestion}
            </pre>
          )}
        </div>
      )}

      {/* AWS Action Result (for non-code-fix actions) */}
      {actionType !== 'code_fix' && pr.aws_result && (
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-4 h-4 text-orange-400" />
            <h3 className="text-sm font-semibold text-orange-300">AWS Action Executed</h3>
            <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded ml-auto ${
              pr.aws_result.success ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'
            }`}>
              {pr.aws_result.success ? 'SUCCESS' : 'FAILED'}
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-white/40 w-24">Action:</span>
              <span className="text-white/70 font-mono">{pr.action_type}</span>
            </div>
            {pr.aws_result.instance_id && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-white/40 w-24">Instance:</span>
                <span className="text-white/70 font-mono">{pr.aws_result.instance_id}</span>
              </div>
            )}
            {pr.aws_result.message && (
              <div className="flex items-start gap-2 text-xs">
                <span className="text-white/40 w-24">Result:</span>
                <span className="text-white/70">{pr.aws_result.message}</span>
              </div>
            )}
            {pr.aws_result.commands && (
              <div className="mt-2">
                <p className="text-xs text-white/40 mb-1">Commands executed:</p>
                <pre className="p-2 bg-black/40 rounded-lg text-[11px] text-orange-200 overflow-x-auto border border-orange-500/10">
                  {pr.aws_result.commands.join('\n')}
                </pre>
              </div>
            )}
            {pr.aws_result.error && (
              <div className="mt-2 p-2 bg-red-500/5 rounded-lg border border-red-500/10">
                <p className="text-xs text-red-300">{pr.aws_result.error}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Connector Write Activity */}
      {activity.length > 0 && (
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white/80">Connector write activity</h3>
              <p className="text-xs text-white/40">Ordered events from connector action reports</p>
            </div>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded bg-white/5 text-white/50 border border-white/10">
              {activity.length} EVENTS
            </span>
          </div>
          <div className="space-y-2">
            {activity.map((a) => (
              <ActivityEvent key={a.id} activity={a} />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}

/* ─── Main App ─── */
export default function App() {
  const [dashboard, setDashboard] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [selectedIncident, setSelectedIncident] = useState(null)
  const [testInput, setTestInput] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [activeNav, setActiveNav] = useState('dashboard')

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [dashRes, incRes] = await Promise.all([
        api.get('/dashboard'),
        api.get('/incidents'),
      ])
      setDashboard(dashRes.data)
      setIncidents(incRes.data.incidents || [])
    } catch (e) {}
  }

  const handleTestIncident = async () => {
    if (!testInput.trim() || isProcessing) return
    setIsProcessing(true)
    try {
      const res = await api.post('/incidents', {
        description: testInput,
        reporter: 'Dashboard User',
        source: 'dashboard',
      })
      setSelectedIncident(res.data)
      setTestInput('')
      loadData()
    } catch (e) {
      console.error(e)
    }
    setIsProcessing(false)
  }

  const viewIncident = async (id) => {
    try {
      const res = await api.get(`/incidents/${id}`)
      setSelectedIncident(res.data)
    } catch (e) {}
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <div className="w-60 border-r border-white/5 p-5 flex flex-col bg-dark-900/50">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-8">
          <div className="w-8 h-8 rounded-lg bg-brand-500/20 flex items-center justify-center">
            <Zap className="w-4 h-4 text-brand-500" />
          </div>
          <div>
            <span className="font-bold text-base">runbook</span>
            <p className="text-[10px] text-white/30">Incident Command</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="space-y-1 mb-6">
          {[
            { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
            { id: 'inbox', icon: Inbox, label: 'Inbox' },
            { id: 'memory', icon: Database, label: 'Memory' },
            { id: 'settings', icon: Settings, label: 'Settings' },
          ].map(item => (
            <button
              key={item.id}
              onClick={() => { setActiveNav(item.id); setSelectedIncident(null); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeNav === item.id
                  ? 'bg-brand-500/10 text-brand-500 font-medium'
                  : 'text-white/50 hover:bg-white/5 hover:text-white/70'
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </nav>

        {/* Workspace */}
        <div className="mb-6">
          <p className="text-[10px] uppercase tracking-widest text-white/25 mb-2 px-3">Workspace</p>
          <div className="flex items-center gap-2 px-3 py-2 text-sm text-white/60">
            <ChevronRight className="w-3 h-3" /> Incident Command
          </div>
        </div>

        {/* Connected Apps */}
        <div className="mb-6">
          <p className="text-[10px] uppercase tracking-widest text-white/25 mb-2 px-3">Connected Apps</p>
          <div className="space-y-1">
            <div className="flex items-center justify-between px-3 py-2">
              <div className="flex items-center gap-2 text-sm text-white/60">
                <MessageSquare className="w-3.5 h-3.5 text-blue-400" /> Discord
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            </div>
            <div className="flex items-center justify-between px-3 py-2">
              <div className="flex items-center gap-2 text-sm text-white/60">
                <GitBranch className="w-3.5 h-3.5 text-purple-400" /> GitHub
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            </div>
          </div>
        </div>

        {/* Bottom status */}
        <div className="mt-auto space-y-2">
          <div className="flex items-center gap-2 px-3 py-2 text-xs text-white/40">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Bridge reachable
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        <AnimatePresence mode="wait">
          {selectedIncident ? (
            <IncidentDetail
              key="detail"
              incident={selectedIncident}
              onBack={() => setSelectedIncident(null)}
            />
          ) : (
            <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-bold text-white/90">Dashboard</h1>
                  <p className="text-xs text-white/40">Runbook Incident Command</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  <span className="text-xs text-white/50">Pipeline active</span>
                </div>
              </div>

              {/* Stats */}
              {dashboard && (
                <div className="grid grid-cols-4 gap-4">
                  {[
                    { label: 'Total', value: dashboard.stats.total, color: 'text-white/90' },
                    { label: 'Resolved', value: dashboard.stats.resolved, color: 'text-emerald-400' },
                    { label: 'Active', value: dashboard.stats.active, color: 'text-yellow-400' },
                    { label: 'Failed', value: dashboard.stats.failed, color: 'text-red-400' },
                  ].map(s => (
                    <div key={s.label} className="bg-white/[0.02] border border-white/5 rounded-xl p-4 text-center">
                      <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                      <p className="text-xs text-white/40 mt-1">{s.label}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Test input */}
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
                <p className="text-xs text-white/40 mb-3">Simulate an incident (or use Discord: <code className="text-brand-500">!incident &lt;description&gt;</code>)</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={testInput}
                    onChange={(e) => setTestInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleTestIncident()}
                    placeholder="e.g., Users reporting 500 errors on the login page..."
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-white/25 outline-none focus:border-brand-500/50 transition-colors"
                    disabled={isProcessing}
                  />
                  <button
                    onClick={handleTestIncident}
                    disabled={!testInput.trim() || isProcessing}
                    className="px-5 py-2.5 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm font-medium disabled:opacity-30 transition-all"
                  >
                    {isProcessing ? 'Processing...' : 'Run Pipeline'}
                  </button>
                </div>
              </div>

              {/* Recent Incidents */}
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-white/70 mb-4">Recent Incidents</h3>
                {incidents.length === 0 ? (
                  <p className="text-sm text-white/30 text-center py-8">No incidents yet. Report one via Discord or the test input above.</p>
                ) : (
                  <div className="space-y-2">
                    {incidents.map(inc => (
                      <div
                        key={inc.id}
                        onClick={() => viewIncident(inc.id)}
                        className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-xl hover:border-white/10 hover:bg-white/[0.04] cursor-pointer transition-all"
                      >
                        <div className="flex items-center gap-3">
                          <AlertTriangle className={`w-4 h-4 ${
                            inc.severity === 'critical' ? 'text-red-400' :
                            inc.severity === 'high' ? 'text-orange-400' : 'text-yellow-400'
                          }`} />
                          <div>
                            <p className="text-sm text-white/80 font-medium">{inc.title || inc.description?.slice(0, 60)}</p>
                            <p className="text-xs text-white/30 mt-0.5">{inc.reporter} · {inc.source} · {inc.created_at?.slice(0, 10)}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <SeverityBadge severity={inc.severity} />
                          <StatusBadge status={inc.status} />
                          <ChevronRight className="w-4 h-4 text-white/20" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
