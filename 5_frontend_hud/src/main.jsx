import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import dtnManager, { DTN_COMM_MODES } from '../../4_offline_dtn_layer/dtn_sync_manager.js';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_URL || '';
const IS_GITHUB_PAGES = window.location.hostname.endsWith('github.io');
const CREW = ['ASTRO_01', 'ASTRO_02', 'ASTRO_03', 'ASTRO_04'];
const LABELS = {
  ASTRO_01: 'Crew member 01',
  ASTRO_02: 'Crew member 02',
  ASTRO_03: 'Crew member 03',
  ASTRO_04: 'Crew member 04',
};

const CREW_METRICS = [
  { key: 'heart_rate_bpm', label: 'HEART RATE', unit: 'bpm', digits: 0 },
  { key: 'spo2_percent', label: 'SpO₂', unit: '%', digits: 0 },
  { key: 'body_temp_c', label: 'Temperature', unit: '°C', digits: 1 },
  { key: 'systolic_bp_mmhg', label: 'Systolic', unit: 'mmHg', digits: 0 },
  { key: 'neutron_radiation_msv_hr', label: 'RADIATION', unit: 'mSv/h', digits: 3 },
  { key: 'gravity_level_g', label: 'Gravity', unit: 'g', digits: 2 },
];

const EXTENDED_METRICS = [
  { key: 'respiratory_rate_rpm', label: 'Resp. rate', unit: 'rpm', digits: 1 },
  { key: 'diastolic_bp_mmhg', label: 'Diastolic', unit: 'mmHg', digits: 0 },
  { key: 'blood_sugar_mg_dl', label: 'Blood sugar', unit: 'mg/dL', digits: 0 },
  { key: 'intracranial_pressure_idx', label: 'ICP index', unit: '', digits: 1 },
  { key: 'bone_density_loss_pct', label: 'Bone density', unit: '% loss', digits: 2 },
  { key: 'mood_stress_score', label: 'Stress score', unit: '/10', digits: 0 },
  { key: 'sleep_hours_24h', label: 'Sleep (24h)', unit: 'h', digits: 1 },
  { key: 'comm_latency_sec', label: 'Latency', unit: 'sec', digits: 0 },
];

const HEALTH_SUMMARY_METRICS = [
  { key: 'heart_rate_bpm', label: 'Heart rate', unit: 'bpm', digits: 0 },
  { key: 'spo2_percent', label: 'SpO₂', unit: '%', digits: 0 },
  { key: 'body_temp_c', label: 'Temperature', unit: '°C', digits: 1 },
  { key: 'systolic_bp_mmhg', label: 'Systolic BP', unit: 'mmHg', digits: 0 },
  { key: 'diastolic_bp_mmhg', label: 'Diastolic BP', unit: 'mmHg', digits: 0 },
  { key: 'respiratory_rate_rpm', label: 'Resp. rate', unit: 'rpm', digits: 1 },
  { key: 'neutron_radiation_msv_hr', label: 'Radiation', unit: 'mSv/h', digits: 3 },
  { key: 'intracranial_pressure_idx', label: 'ICP index', unit: '', digits: 1 },
];

const RISK_READING_GROUPS = [
  { terms: ['hypoxia'], keys: ['spo2_percent', 'respiratory_rate_rpm'] },
  { terms: ['radiation'], keys: ['neutron_radiation_msv_hr'] },
  { terms: ['sans', 'neuro', 'ocular'], keys: ['intracranial_pressure_idx', 'bone_density_loss_pct'] },
  { terms: ['cardiovascular', 'heart', 'eva_stress'], keys: ['heart_rate_bpm', 'systolic_bp_mmhg', 'diastolic_bp_mmhg', 'mood_stress_score'] },
];

const STREAM_METRICS = [
  { key: 'heart_rate_bpm', label: 'Heart Rate', detail: 'HEART RATE', unit: 'bpm', digits: 0, color: '#5EF2D0' },
  { key: 'spo2_percent', label: 'Blood Oxygen SpO₂', detail: 'SpO₂', unit: '%', digits: 0, color: '#38BDF8' },
  { key: 'neutron_radiation_msv_hr', label: 'Neutron Radiation', detail: 'RADIATION', unit: 'mSv/h', digits: 3, color: '#FBBF24' },
];

const DOMAINS = [
  { label: 'Cardiovascular', terms: ['cardiovascular', 'heart', 'blood_pressure'] },
  { label: 'Respiratory', terms: ['hypoxia', 'respiratory', 'oxygen'] },
  { label: 'Radiation exposure', terms: ['radiation'] },
  { label: 'Bone & muscle', terms: ['bone', 'muscle'] },
  { label: 'Neuro & sleep', terms: ['sans', 'neuro', 'intracranial', 'sleep'] },
];

const STAR_POSITIONS = [
  { left: '8%', top: '12%' }, { left: '22%', top: '5%' }, { left: '37%', top: '17%' },
  { left: '53%', top: '8%' }, { left: '71%', top: '19%' }, { left: '92%', top: '12%' },
  { left: '15%', top: '42%' }, { left: '43%', top: '36%' }, { left: '82%', top: '48%' },
  { left: '28%', top: '78%' }, { left: '66%', top: '86%' },
];

function statusToken(status = 'Awaiting') {
  const normalized = String(status).toLowerCase();
  if (normalized === 'normal' || normalized === 'nominal') return 'nominal';
  if (normalized === 'warning') return 'warning';
  if (normalized === 'critical') return 'critical';
  return 'loading';
}

function statusLabel(status = 'Awaiting') {
  const token = statusToken(status);
  if (token === 'nominal') return 'NOMINAL';
  if (token === 'warning') return 'WARNING';
  if (token === 'critical') return 'CRITICAL';
  return 'AWAITING';
}

function getCrewHealthAssessment(sample = {}) {
  const rawRisk = String(sample.detected_nasa_risk || 'Healthy_Baseline');
  const normalizedRisk = rawRisk.toLowerCase();
  const isBaselineRisk = normalizedRisk === 'healthy_baseline';
  const modelStatus = sample.health_status || (isBaselineRisk ? 'Awaiting' : 'Warning');
  const status = statusToken(modelStatus) === 'nominal' && !isBaselineRisk ? 'Warning' : modelStatus;
  const token = statusToken(status);
  const risk = formatRisk(rawRisk);
  const riskGroup = RISK_READING_GROUPS.find((group) => group.terms.some((term) => normalizedRisk.includes(term)));
  const riskMetrics = isBaselineRisk ? [] : (riskGroup?.keys || []);
  const availableRiskReadings = riskMetrics
    .map((key) => [...HEALTH_SUMMARY_METRICS, ...EXTENDED_METRICS].find((metric) => metric.key === key))
    .filter((metric) => metric && sample[metric.key] !== null && sample[metric.key] !== undefined && sample[metric.key] !== '')
    .map((metric) => `${metric.label} ${fmt(sample[metric.key], metric.digits)}${metric.unit ? ` ${metric.unit}` : ''}`);
  const currentReadings = HEALTH_SUMMARY_METRICS
    .filter((metric) => sample[metric.key] !== null && sample[metric.key] !== undefined && sample[metric.key] !== '')
    .slice(0, 3)
    .map((metric) => `${metric.label} ${fmt(sample[metric.key], metric.digits)}${metric.unit ? ` ${metric.unit}` : ''}`);

  let summary;
  if (token === 'loading') {
    summary = 'Waiting for this crew member’s first telemetry packet.';
  } else if (token === 'nominal' && isBaselineRisk) {
    summary = currentReadings.length
      ? `No active AI risk flagged. Latest readings: ${currentReadings.join(' · ')}.`
      : 'No active AI risk flagged. Current telemetry is within the nominal AI profile.';
  } else if (availableRiskReadings.length) {
    summary = `${statusLabel(status)} AI signal: ${risk}. Related readings: ${availableRiskReadings.join(' · ')}.`;
  } else {
    const readingSummary = currentReadings.length ? ` Latest readings: ${currentReadings.join(' · ')}.` : '';
    summary = `${statusLabel(status)} health status detected from the latest telemetry. AI risk: ${risk}.${readingSummary}`;
  }

  const fallbackRecommendation = token === 'nominal'
    ? 'Continue standard monitoring.'
    : token === 'critical'
      ? 'Immediate medical attention required; follow the onboard triage protocol.'
      : token === 'warning'
        ? 'Increase monitoring frequency and review the flagged telemetry.'
        : 'Recommendation will appear with the first telemetry assessment.';

  return {
    status,
    token,
    risk,
    summary,
    riskMetrics,
    recommendation: sample.triage_protocol_action || fallbackRecommendation,
  };
}

function fmt(value, digits = 1) {
  if (value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : '—';
}

function formatRisk(value) {
  if (!value) return 'Healthy Baseline';
  return String(value).replaceAll('_', ' ');
}

function confidencePercent(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? Math.max(0, Math.min(100, Math.round(number * 100))) : null;
}

function formatLatency(seconds) {
  if (!Number.isFinite(seconds)) return '—';
  if (seconds >= 60) return `${Math.round(seconds / 60)}m`;
  return `${seconds}s`;
}

function PulseIcon() {
  return (
    <svg viewBox="0 0 48 32" fill="none" aria-hidden="true">
      <path d="M2 17h9l5-11 8 22 7-17 4 6h11" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m5 12.5 4.3 4.2L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3.5 21 20H3L12 3.5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M12 9v5m0 3h.01" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </svg>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={`status-pill ${statusToken(status)}`} aria-label={`Health status ${statusLabel(status)}`}>
      {statusLabel(status)}
    </span>
  );
}

function AnimatedNumber({ value, digits = 0, unit = '', shimmer = false }) {
  const numeric = value === null || value === undefined || value === '' ? null : Number(value);
  const displayRef = useRef(Number.isFinite(numeric) ? numeric : null);
  const [display, setDisplay] = useState(displayRef.current);
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(numeric)) {
      displayRef.current = null;
      setDisplay(null);
      return undefined;
    }

    const start = displayRef.current ?? numeric;
    const changed = displayRef.current !== null && displayRef.current !== numeric;
    const startedAt = performance.now();
    let frame;
    let flashTimer;

    if (changed) {
      setFlash(true);
      flashTimer = window.setTimeout(() => setFlash(false), 380);
    }

    const tick = (now) => {
      const progress = Math.min(1, (now - startedAt) / 300);
      const eased = 1 - (1 - progress) ** 3;
      const next = start + ((numeric - start) * eased);
      displayRef.current = progress === 1 ? numeric : next;
      setDisplay(displayRef.current);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      if (flashTimer) window.clearTimeout(flashTimer);
    };
  }, [numeric]);

  const shown = display === null ? '—' : display.toFixed(digits);
  return (
    <span className={`animated-number ${flash ? 'value-flash' : ''} ${shimmer ? 'shimmer' : ''}`}>
      {shown}{unit && <small>{unit}</small>}
    </span>
  );
}

function StatusDomain({ domain, sample }) {
  const risk = String(sample.detected_nasa_risk || '').toLowerCase();
  const matchesRisk = domain.terms.some((term) => risk.includes(term));
  const status = matchesRisk ? (sample.health_status || 'Normal') : 'Normal';
  const token = statusToken(status);
  const badge = token === 'critical' ? 'CRIT' : token === 'warning' ? 'WARN' : 'OK';
  return (
    <div className={`system-row ${token}`}>
      <span className="system-row-mark" aria-hidden="true"><CheckIcon /></span>
      <span className="system-row-label">{domain.label}</span>
      <span className={`system-badge ${token}`}>{badge}</span>
    </div>
  );
}

function App() {
  const [latest, setLatest] = useState({});
  const [history, setHistory] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [selected, setSelected] = useState(CREW[0]);
  const [connection, setConnection] = useState('Connecting');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [commMode, setCommMode] = useState(dtnManager.getCommMode());
  const [queueCount, setQueueCount] = useState(0);
  const demoLoadedRef = useRef(false);

  const refresh = useCallback(async () => {
    if (IS_GITHUB_PAGES) {
      if (demoLoadedRef.current) return;
      try {
        const response = await fetch(`${API_BASE}demo-telemetry.json`);
        if (!response.ok) throw new Error('Demo telemetry unavailable');
        const demo = await response.json();
        const nextHistory = demo.history || {};
        const nextLatest = Object.fromEntries(
          Object.entries(nextHistory).map(([id, samples]) => [id, samples.at(-1)]).filter(([, sample]) => sample)
        );
        setHistory(nextHistory);
        setLatest(nextLatest);
        setAlerts(demo.alerts || []);
        setLastUpdate(new Date());
        setConnection('Demo');
        demoLoadedRef.current = true;
      } catch {
        setConnection('Offline');
      }
      return;
    }

    try {
      const responses = await Promise.all(
        CREW.map((id) => fetch(`${API_BASE}/api/history/${id}?limit=60`, { cache: 'no-store' }).then((response) => {
          if (!response.ok) throw new Error('Backend unavailable');
          return response.json();
        }))
      );
      const nextHistory = {};
      const nextLatest = {};
      responses.forEach((result, index) => {
        const id = CREW[index];
        if (!Array.isArray(result.history) || result.history.length === 0) {
          throw new Error(`Telemetry history missing for ${id}`);
        }
        nextHistory[id] = result.history;
        if (nextHistory[id].length) nextLatest[id] = nextHistory[id][nextHistory[id].length - 1];
      });
      setHistory((old) => ({ ...old, ...nextHistory }));
      setLatest((old) => ({ ...old, ...nextLatest }));
      setLastUpdate(new Date());
      setConnection((old) => (old === 'Live' ? old : 'Polling'));
    } catch {
      setConnection((old) => (old === 'Live' ? 'Polling' : old));
    }
  }, []);

  const refreshAlerts = useCallback(async () => {
    if (IS_GITHUB_PAGES) return;
    try {
      const response = await fetch(`${API_BASE}/api/alerts?limit=12`, { cache: 'no-store' });
      if (response.ok) setAlerts((await response.json()).alerts || []);
    } catch {
      // The live stream and next poll will refresh the panel when the link returns.
    }
  }, []);

  useEffect(() => {
    const unsubscribe = dtnManager.subscribe((state) => {
      setCommMode(state.mode);
      setQueueCount(state.queueCount);
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    refresh();
    refreshAlerts();
    const historyTimer = window.setInterval(refresh, 2500);
    const alertsTimer = window.setInterval(refreshAlerts, 3000);
    let socket;
    let disposed = false;
    let websocketUnavailable = false;

    const connect = () => {
      if (disposed || websocketUnavailable) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsBase = import.meta.env.VITE_API_URL || `${protocol}//${window.location.host}`;
      try {
        socket = new WebSocket(`${wsBase.replace(/^http/, 'ws')}/ws/live-hud`);
      } catch {
        websocketUnavailable = true;
        return;
      }
      socket.onopen = () => {
        setConnection('Live');
        socket.send('ping');
      };
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'TELEMETRY_UPDATE' && message.data) {
            const sample = message.data;
            setLatest((old) => ({ ...old, [sample.astronaut_id]: sample }));
            setHistory((old) => ({
              ...old,
              [sample.astronaut_id]: [...(old[sample.astronaut_id] || []), sample].slice(-60),
            }));
            setLastUpdate(new Date());
            if (sample.health_status !== 'Normal') refreshAlerts();
          }
        } catch {
          // Ignore non-JSON ping acknowledgements.
        }
      };
      socket.onclose = () => {
        if (disposed) return;
        websocketUnavailable = true;
        setConnection((old) => (old === 'Live' ? 'Polling' : old));
      };
      socket.onerror = () => {
        websocketUnavailable = true;
        socket.close();
      };
    };
    if (IS_GITHUB_PAGES) {
      setConnection('Demo');
    } else {
      connect();
    }

    return () => {
      disposed = true;
      window.clearInterval(historyTimer);
      window.clearInterval(alertsTimer);
      socket?.close();
    };
  }, [refresh, refreshAlerts]);

  const selectedHistory = useMemo(
    () => (history[selected] || []).map((sample, index) => ({ ...sample, tick: index + 1 })),
    [history, selected]
  );
  const chartHistory = selectedHistory.slice(-32);
  const crewOnline = Object.keys(latest).length;
  const nominalCount = CREW.filter((id) => latest[id]?.health_status === 'Normal').length;
  const criticalCount = CREW.filter((id) => latest[id]?.health_status === 'Critical').length;
  const warningCount = CREW.filter((id) => latest[id]?.health_status === 'Warning').length;
  const selectedSample = latest[selected] || {};
  const selectedStatus = selectedSample.health_status || 'Awaiting';
  const selectedRisk = formatRisk(selectedSample.detected_nasa_risk);
  const confidence = confidencePercent(selectedSample.confidence);
  const maxLinkDelay = Math.max(0, ...CREW.map((id) => Number(latest[id]?.comm_latency_sec || 0)));
  const missionDay = selectedSample.mission_day;
  const updatedAt = lastUpdate || new Date();
  const utcDate = updatedAt.toISOString().replace('T', ' ').slice(0, 16);
  const modeKey = commMode?.id || 'LUNAR';
  const linkModes = Object.values(DTN_COMM_MODES);

  return (
    <>
      <div className="space-backdrop" aria-hidden="true">
        {STAR_POSITIONS.map((position, index) => <i className={`star star-${index + 1}`} style={position} key={index} />)}
        <div className="moon" />
        <div className="earth" />
      </div>
      <main className="shell" id="top">
        <header className="topbar glass-card">
          <a className="brand" href="#top" aria-label="AstroPulse mission overview">
            <span className="brand-mark"><PulseIcon /></span>
            <span className="brand-type"><strong><b>ASTRO</b><em>PULSE</em></strong><small>MISSION HEALTH SYSTEM</small><small className="standards">NASA HRP · CSA CANS · PhysioNet</small></span>
          </a>
          <div className="topbar-center">
            <div className="earth-link">
              <span className="top-label">EARTH LINK</span>
              <div className="link-modes" aria-label={`Earth link mode ${commMode?.label || 'Lunar'}`}>
                {linkModes.map((mode) => (
                  <span className={`mode-chip ${mode.id.toLowerCase()} ${modeKey === mode.id ? 'active' : ''}`} key={mode.id}>
                    <b>{mode.id}</b><small>{formatLatency(mode.latencySec)}</small>
                  </span>
                ))}
              </div>
            </div>
            <div className="mission-label"><span>ARTEMIS DEEP SPACE</span><i /> <span>FLIGHT DAY 014</span></div>
          </div>
          <div className="topbar-right">
            <span className="queue-chip"><span className="queue-mark" aria-hidden="true"><CheckIcon /></span>DTN Queue {queueCount === 0 ? 'clear' : `${queueCount} pending`}</span>
            <div className={`connection ${connection.toLowerCase()}`} aria-live="polite"><i /> {connection}</div>
          </div>
        </header>

        <div className="unified-dashboard">
        <section className="intro" aria-label="Mission summary">
          <div className="intro-copy">
            <p className="eyebrow">MISSION CONTROL HUD</p>
            <p className="eyebrow original-eyebrow">CREW TELEMETRY · LIVE TRIAGE</p>
            <h1>Mission control<span>.</span></h1>
            <p className="subhead">Physiological monitoring and AI-assisted crew health overview.</p>
          </div>
          <div className="mission-readiness">
            <span className={`readiness-badge ${statusToken(criticalCount ? 'Critical' : warningCount ? 'Warning' : 'Normal')}`}>
              <i /> {criticalCount ? 'CRITICAL' : warningCount ? 'WARNING' : crewOnline ? 'NOMINAL' : 'AWAITING'}
            </span>
            <strong><b>{nominalCount} NOM</b><i>·</i><b>{warningCount} WARN</b><i>·</i><b>{criticalCount} CRIT</b></strong>
          </div>
          <div className="mission-meta">
            <span className="met"><small>MET</small><b>D+{fmt(missionDay, 0)}</b></span>
            <span className="utc-clock"><small>DATE / UTC</small><b>{utcDate} UTC</b></span>
            <span className="realtime-chip"><i /> {IS_GITHUB_PAGES ? 'DEMO SNAPSHOT' : 'REAL-TIME'}</span>
            <div className="updated"><span>LAST UPDATE</span><strong>{lastUpdate ? lastUpdate.toLocaleTimeString() : 'Awaiting telemetry'}</strong></div>
          </div>
        </section>

        <section className="summary-grid" aria-label="Mission summary">
          <article className="summary-card glass-card"><span>ACTIVE CREW</span><strong><AnimatedNumber value={crewOnline} digits={0} /><small> / 4</small></strong><em>Telemetry linked</em></article>
          <article className="summary-card glass-card"><span>CRITICAL</span><strong className={criticalCount ? 'text-critical' : ''}><AnimatedNumber value={criticalCount} digits={0} /></strong><em>Immediate attention</em></article>
          <article className="summary-card glass-card"><span>WARNING</span><strong className={warningCount ? 'text-warning' : ''}><AnimatedNumber value={warningCount} digits={0} /></strong><em>Monitoring required</em></article>
          <article className="summary-card glass-card"><span>MAX LINK DELAY</span><strong className="link-value"><AnimatedNumber value={maxLinkDelay} digits={0} /><small> sec</small></strong><em>Current crew estimate</em></article>
        </section>

        <section className="overview-roster glass-card" aria-label="Crew readiness health summary">
          <div className="overview-roster-heading">
            <div><p className="eyebrow">CREW READINESS</p><h2>Team status</h2></div>
            <span className="section-note">LIVE AI ASSESSMENT · {CREW.length} CREW</span>
          </div>
          <div className="crew-health-grid">
            {CREW.map((id, index) => {
              const sample = latest[id] || {};
              const assessment = getCrewHealthAssessment(sample);
              const extraRiskReadings = assessment.riskMetrics
                .filter((key) => !HEALTH_SUMMARY_METRICS.some((metric) => metric.key === key))
                .map((key) => [...HEALTH_SUMMARY_METRICS, ...EXTENDED_METRICS].find((metric) => metric.key === key))
                .filter((metric) => metric && sample[metric.key] !== null && sample[metric.key] !== undefined && sample[metric.key] !== '');
              return (
                <article className={`crew-health-card glass-card state-${assessment.token}`} key={id}>
                  <div className="health-card-head">
                    <div className="health-identity">
                      <span className="health-avatar">A{index + 1}</span>
                      <div><small>MISSION CREW</small><h3>{id}</h3></div>
                    </div>
                    <StatusBadge status={assessment.status} />
                  </div>
                  <div className={`health-condition state-${assessment.token}`}>
                    <span className="health-overline">HEALTH CONDITION</span>
                    <p>{assessment.summary}</p>
                  </div>
                  <div className="health-reading-heading">
                    <span>LIVE VITALS</span>
                    <small>{assessment.token === 'nominal' ? 'NO AI FLAGS' : assessment.token === 'loading' ? 'AWAITING DATA' : 'AI-RELATED SIGNALS'}</small>
                  </div>
                  <div className="health-metric-grid">
                    {HEALTH_SUMMARY_METRICS.map((metric) => {
                      const hasReading = sample[metric.key] !== null && sample[metric.key] !== undefined && sample[metric.key] !== '';
                      const isRelated = assessment.riskMetrics.includes(metric.key);
                      return (
                        <div className={`health-metric ${isRelated ? 'related' : ''}`} key={metric.key}>
                          <span>{metric.label}</span>
                          <strong>{hasReading ? <AnimatedNumber value={sample[metric.key]} digits={metric.digits} unit={metric.unit ? ` ${metric.unit}` : ''} shimmer={!latest[id]} /> : '—'}</strong>
                          {isRelated && <em>AI SIGNAL</em>}
                        </div>
                      );
                    })}
                  </div>
                  {extraRiskReadings.length > 0 && (
                    <div className="health-related-readings">
                      <span>ADDITIONAL AI SIGNALS</span>
                      <strong>{extraRiskReadings.map((metric) => `${metric.label} ${fmt(sample[metric.key], metric.digits)}${metric.unit ? ` ${metric.unit}` : ''}`).join(' · ')}</strong>
                    </div>
                  )}
                  <div className={`health-risk-row state-${assessment.token}`}>
                    <span>DETECTED AI RISK</span>
                    <strong>{assessment.risk}</strong>
                  </div>
                  <div className={`health-recommendation state-${assessment.token}`}>
                    <span className="health-recommendation-mark" aria-hidden="true">{assessment.token === 'critical' || assessment.token === 'warning' ? <AlertIcon /> : <CheckIcon />}</span>
                    <div><span className="health-overline">AI RECOMMENDATION</span><p>{assessment.recommendation}</p></div>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="section-heading page-heading">
          <div><p className="eyebrow">LIVE BIO-TELEMETRY STREAM</p><h1 className="page-title">Crew telemetry</h1></div>
          <span className="section-note">{selected} · {statusLabel(selectedStatus)}</span>
        </section>
        <section className="telemetry-toolbar glass-card" aria-label="Choose crew member for telemetry">
          <div className="telemetry-toolbar-label"><span className="eyebrow">SELECTED CREW</span><strong>{LABELS[selected]}</strong></div>
          <div className="crew-switcher" role="group" aria-label="Select crew member">
            {CREW.map((id, index) => (
              <button className={selected === id ? 'selected' : ''} type="button" onClick={() => setSelected(id)} aria-pressed={selected === id} key={id}>
                <span>A{index + 1}</span>{id}
              </button>
            ))}
          </div>
        </section>
        <section className="detail-grid telemetry-layout" id="telemetry">
          <article className="panel chart-panel glass-card">
            <div className="subsection-heading">
              <div><p className="eyebrow">LIVE TELEMETRY — {selected}</p><h2>{LABELS[selected]}</h2></div>
              <StatusBadge status={selectedStatus} />
            </div>
            <div className="stream-card-stack">
              {STREAM_METRICS.map((metric) => {
                const areaId = `area-${selected}-${metric.key}`;
                return (
                  <section className={`stream-metric-card ${statusToken(selectedStatus)}`} key={metric.key} style={{ '--metric-color': metric.color }}>
                    <div className="stream-metric-head"><span>{metric.label}</span><strong><AnimatedNumber value={selectedSample[metric.key]} digits={metric.digits} unit={metric.unit} shimmer={!latest[selected]} /></strong></div>
                    <div className="area-chart" role="img" aria-label={`${metric.label} live trend for ${selected}`}>
                      {chartHistory.length ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={chartHistory} margin={{ top: 3, right: 2, left: 2, bottom: 0 }}>
                            <defs><linearGradient id={areaId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={metric.color} stopOpacity={0.45} /><stop offset="100%" stopColor={metric.color} stopOpacity={0} /></linearGradient></defs>
                            <Area type="monotone" dataKey={metric.key} stroke={metric.color} strokeWidth={2} fill={`url(#${areaId})`} isAnimationActive animationDuration={300} animationEasing="ease-out" dot={false} activeDot={false} />
                          </AreaChart>
                        </ResponsiveContainer>
                      ) : <div className="chart-placeholder shimmer">—</div>}
                    </div>
                  </section>
                );
              })}
            </div>

            <section className="extended-vitals glass-inset">
              <div className="extended-heading"><span className="eyebrow">EXTENDED VITALS</span><span className="section-note">{selected}</span></div>
              <div className="extended-grid">
                {EXTENDED_METRICS.map((metric) => (
                  <div className="extended-tile" key={metric.key}>
                    <span>{metric.label}</span>
                    <strong><AnimatedNumber value={selectedSample[metric.key]} digits={metric.digits} unit={metric.unit ? ` ${metric.unit}` : ''} shimmer={!latest[selected]} /></strong>
                  </div>
                ))}
              </div>
            </section>

            <div className="legacy-chart-heading">
              <div><p className="eyebrow">VITALS TREND</p><h2>{LABELS[selected]}</h2></div>
              <StatusBadge status={selectedStatus} />
            </div>
            <div className="chart-legend"><span><i className="legend-heart" /> HEART RATE <b>{fmt(selectedSample.heart_rate_bpm)} bpm</b></span><span><i className="legend-oxygen" /> SpO₂ <b>{fmt(selectedSample.spo2_percent)}%</b></span></div>
            <div className="chart-wrap" role="img" aria-label={`Vitals trend, heart rate and SpO2, ${selected}`}>
              {selectedHistory.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={selectedHistory} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(207,230,255,.12)" strokeDasharray="3 5" vertical={false} />
                    <XAxis dataKey="tick" tick={{ fill: '#9DB4D0', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="heart" domain={['auto', 'auto']} tick={{ fill: '#9DB4D0', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="oxygen" orientation="right" domain={[85, 100]} hide />
                    <Tooltip contentStyle={{ background: 'rgba(10,19,48,.96)', border: '1px solid rgba(255,255,255,.16)', borderRadius: 12, color: '#F2F8FF' }} labelFormatter={(value) => `Sample ${value}`} />
                    <Line yAxisId="heart" type="monotone" dataKey="heart_rate_bpm" name="Heart rate" stroke="#5EF2D0" strokeWidth={2} dot={false} isAnimationActive animationDuration={300} />
                    <Line yAxisId="oxygen" type="monotone" dataKey="spo2_percent" name="SpO₂" stroke="#38BDF8" strokeWidth={2} dot={false} isAnimationActive animationDuration={300} />
                  </LineChart>
                </ResponsiveContainer>
              ) : <div className="empty-chart shimmer">Waiting for the first telemetry packet…</div>}
            </div>
            <div className="chart-foot"><span>RECENT TELEMETRY SAMPLES</span><span>{selectedHistory.length} POINTS</span></div>
          </article>
        </section>

        <section className="section-heading page-heading">
          <div><p className="eyebrow">AUTONOMOUS MEDICAL TRIAGE</p><h1 className="page-title">Medical alerts</h1></div>
          <span className="section-note">{alerts.length} RECENT ALERTS</span>
        </section>
        <section className="detail-grid alerts-layout">
          <article className="panel alert-panel glass-card">
            <div className="triage-label-row">
              <div><p className="eyebrow">AUTONOMOUS MEDICAL TRIAGE — {selected}</p><h2>Mission health assessment</h2></div>
              <span className="system-status">SYSTEM: {statusLabel(selectedStatus) === 'NOMINAL' ? 'ALL SYSTEMS NOMINAL' : statusLabel(selectedStatus)}</span>
            </div>
            <section className={`triage-card state-${statusToken(selectedStatus)}`}>
              <div className="triage-header">
                <span className={`triage-icon ${statusToken(selectedStatus)}`}>
                  {statusToken(selectedStatus) === 'critical' || statusToken(selectedStatus) === 'warning' ? <AlertIcon /> : <CheckIcon />}
                </span>
                <div className="triage-title"><span className="eyebrow">AUTONOMOUS MEDICAL TRIAGE</span><strong>{selectedRisk}</strong></div>
                <StatusBadge status={selectedStatus} />
              </div>
              <div className="triage-body">
                <div className="gauge-column">
                  <div className={`confidence-gauge state-${statusToken(selectedStatus)}`} role="img" aria-label={`AI confidence ${confidence === null ? 'not available' : `${confidence} percent`}`}>
                    <svg viewBox="0 0 270 270" aria-hidden="true">
                      <defs><linearGradient id="gauge-progress" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#5EF2D0" /><stop offset="100%" stopColor="#38BDF8" /></linearGradient></defs>
                      <circle className="gauge-track" cx="135" cy="135" r="106" />
                      <circle className="gauge-progress" cx="135" cy="135" r="106" style={{ '--gauge-progress': confidence === null ? 0 : confidence / 100 }} />
                      <circle className="gauge-dash" cx="135" cy="135" r="123" />
                    </svg>
                    <div className="gauge-center"><strong>{confidence === null ? '—' : `${confidence}%`}</strong><span>{statusToken(selectedStatus) === 'nominal' ? 'ALL VITALS NOMINAL' : `${statusLabel(selectedStatus)} TRIAGE STATUS`}</span></div>
                  </div>
                </div>
                <div className="system-column">
                  <p className="system-heading">SYSTEM: {statusToken(selectedStatus) === 'nominal' ? 'ALL SYSTEMS NOMINAL' : statusLabel(selectedStatus)}</p>
                  <div className="system-checks">{DOMAINS.map((domain) => <StatusDomain domain={domain} sample={selectedSample} key={domain.label} />)}</div>
                  <p className="triage-action">{selectedSample.triage_protocol_action || 'Routine ARCHeR & Tempus Pro monitoring active'}</p>
                </div>
              </div>
              <div className="confidence-footer">
                <span>AI CONFIDENCE</span>
                <div className="confidence-bar" aria-hidden="true"><i style={{ width: `${confidence ?? 0}%` }} /></div>
                <strong>{confidence === null ? '—' : `${confidence}%`}</strong>
              </div>
            </section>

            <div className="alerts-section-heading">
              <div><p className="eyebrow">AI TRIAGE FEED</p><h2>Medical alerts</h2></div>
              <span className="alert-count">{alerts.length} RECENT</span>
            </div>
            <div className="alert-list">
              {alerts.length ? alerts.slice(0, 8).map((alert) => (
                <div className={`alert-item ${statusToken(alert.health_status)}`} key={alert.id}>
                  <div className={`alert-icon ${statusToken(alert.health_status)}`}><AlertIcon /></div>
                  <div className="alert-copy"><strong>{alert.detected_nasa_risk?.replaceAll('_', ' ') || 'Crew health alert'}</strong><span>{LABELS[alert.astronaut_id] || alert.astronaut_id} · {statusLabel(alert.health_status)}</span><small>{alert.triage_protocol_action}</small></div>
                  <time>{alert.timestamp?.slice(11, 16) || '—'}</time>
                </div>
              )) : <div className="empty-alerts"><span className="empty-check"><CheckIcon /></span><strong>No active alerts</strong><small>Alerts will appear here when telemetry requires attention.</small></div>}
            </div>
            <div className="panel-foot">MONITORING {crewOnline} CREW MEMBER{crewOnline === 1 ? '' : 'S'}</div>
          </article>
        </section>
        </div>

        <footer><span>ASTROPULSE <b>·</b> CREW HEALTH MONITOR</span><span>SIMULATED TELEMETRY · FOR DEMONSTRATION</span></footer>
        <div className="reference-footer">AstroPulse v1.0 · NASA Space Apps 2026 · NASA-STD-3001 HRI · CSA CANS · PhysioNet</div>
      </main>
    </>
  );
}

createRoot(document.getElementById('root')).render(<App />);
