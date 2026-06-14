import { useEffect, useState, useCallback } from "react";
import { Grid, Box, Typography, Chip } from "@mui/material";
import MonitorHeartIcon from "@mui/icons-material/MonitorHeart";
import SignalCellularAltIcon from "@mui/icons-material/SignalCellularAlt";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ChecklistIcon from "@mui/icons-material/Checklist";
import SummaryCard from "../components/SummaryCard";
import MetricChart from "../components/MetricChart";
import AnomalyTable from "../components/AnomalyTable";
import AuditTable from "../components/AuditTable";
import { fetchStatus, fetchAnomalies, fetchAudit, fetchSignals } from "../services/api";

const statusColor = { ok: "#22c55e", degraded: "#f59e0b", down: "#f87171" };

const MAPE = [
  { name: "Monitor", desc: "Health checks & metrics" },
  { name: "Analyze", desc: "Root cause detection" },
  { name: "Plan", desc: "Recovery strategy" },
  { name: "Execute", desc: "Docker actions" },
  { name: "Knowledge", desc: "SQLite audit store" },
];

function generateMetrics(base, range, count = 12) {
  return Array.from({ length: count }, (_, i) => ({
    time: `${i}m`,
    value: Math.max(0, base + Math.floor((Math.random() - 0.5) * range)),
  }));
}

export default function Dashboard() {
  const [summary, setSummary] = useState({ status: "ok", signals: 0, anomalies: 0, audits: 0 });
  const [anomalies, setAnomalies] = useState([]);
  const [audit, setAudit] = useState([]);
  const [cpuData, setCpuData] = useState(generateMetrics(45, 30));
  const [rtData, setRtData] = useState(generateMetrics(130, 80));
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const refresh = useCallback(async () => {
    try {
      const s = await fetchStatus();
      setSummary(s.summary ?? s);
    } catch {}
    try { setAnomalies(await fetchAnomalies()); } catch {}
    try { setAudit(await fetchAudit()); } catch {}
    setCpuData(generateMetrics(45, 30));
    setRtData(generateMetrics(130, 80));
    setLastRefresh(new Date());
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6" fontWeight={700}>Overview</Typography>
        <Chip label={`Updated ${lastRefresh.toLocaleTimeString()}`} size="small" sx={{ bgcolor: "#1a1d2e", color: "#475569", border: "1px solid #2d3149", fontSize: 11 }} />
      </Box>

      <Grid container spacing={2} mb={3}>
        <Grid item xs={3}><SummaryCard label="Status" value={summary.status?.toUpperCase()} sub="bookshop service" icon={<MonitorHeartIcon />} color={statusColor[summary.status] || "#6366f1"} /></Grid>
        <Grid item xs={3}><SummaryCard label="Signals" value={summary.signals} sub="health checks" icon={<SignalCellularAltIcon />} color="#6366f1" /></Grid>
        <Grid item xs={3}><SummaryCard label="Anomalies" value={summary.anomalies} sub="detected events" icon={<WarningAmberIcon />} color={summary.anomalies > 0 ? "#f59e0b" : "#22c55e"} /></Grid>
        <Grid item xs={3}><SummaryCard label="Audits" value={summary.audits} sub="recovery actions" icon={<ChecklistIcon />} color="#818cf8" /></Grid>
      </Grid>

      <Typography variant="caption" color="text.secondary" textTransform="uppercase" letterSpacing="0.06em" display="block" mb={1}>MAPE-K Pipeline</Typography>
      <Box display="flex" gap={0} mb={3} borderRadius={2} overflow="hidden" border="1px solid #2d3149">
        {MAPE.map((s, i) => (
          <Box key={s.name} flex={1} p={1.5} bgcolor={i < 4 ? "#1e2040" : "#1a1d2e"}
            sx={{ borderRight: i < 4 ? "1px solid #2d3149" : "none" }}>
            <Typography variant="caption" color="#818cf8" fontWeight={600} textTransform="uppercase" letterSpacing="0.06em" display="block">{s.name}</Typography>
            <Typography variant="caption" color="text.secondary" fontSize={11}>{s.desc}</Typography>
          </Box>
        ))}
      </Box>

      <Typography variant="caption" color="text.secondary" textTransform="uppercase" letterSpacing="0.06em" display="block" mb={1}>Live Metrics</Typography>
      <Grid container spacing={2} mb={3}>
        <Grid item xs={6}><MetricChart title="CPU Usage %" data={cpuData} dataKey="value" color="#6366f1" unit="%" /></Grid>
        <Grid item xs={6}><MetricChart title="Response Time (ms)" data={rtData} dataKey="value" color="#f59e0b" unit="ms" /></Grid>
      </Grid>

      <Typography variant="caption" color="text.secondary" textTransform="uppercase" letterSpacing="0.06em" display="block" mb={1}>Anomalies</Typography>
      <Box mb={3}><AnomalyTable rows={anomalies} /></Box>

      <Typography variant="caption" color="text.secondary" textTransform="uppercase" letterSpacing="0.06em" display="block" mb={1}>Recovery Audit</Typography>
      <AuditTable rows={audit} />
    </Box>
  );
}