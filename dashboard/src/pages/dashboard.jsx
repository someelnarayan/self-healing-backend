import { useEffect, useState, useCallback } from "react";
import { Grid, Box, Typography, Chip, Paper } from "@mui/material";
import MonitorHeartIcon from "@mui/icons-material/MonitorHeart";
import SignalCellularAltIcon from "@mui/icons-material/SignalCellularAlt";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ChecklistIcon from "@mui/icons-material/Checklist";
import SummaryCard from "../components/SummaryCard";
import MetricChart from "../components/MetricChart";
import AnomalyTable from "../components/AnomalyTable";
import AuditTable from "../components/AuditTable";
import { fetchStatus, fetchAnomalies, fetchAudit } from "../services/api";

const statusColor = { ok: "#22c55e", degraded: "#f59e0b", down: "#f87171" };

const MAPE = [
  { name: "Monitor",   desc: "Health checks & metrics",  color: "#6366f1" },
  { name: "Analyze",   desc: "Root cause detection",     color: "#818cf8" },
  { name: "Plan",      desc: "Recovery strategy",        color: "#a5b4fc" },
  { name: "Execute",   desc: "Docker actions",           color: "#f59e0b" },
  { name: "Knowledge", desc: "SQLite audit store",       color: "#22c55e" },
];

function generateMetrics(base, range, count = 14) {
  return Array.from({ length: count }, (_, i) => ({
    time: `${i}m`,
    value: Math.max(0, base + Math.floor((Math.random() - 0.5) * range)),
  }));
}

function SectionLabel({ children }) {
  return (
    <Typography
      variant="caption"
      sx={{
        display: "block",
        color: "#475569",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontWeight: 600,
        fontSize: 11,
        mb: 1.5,
        mt: 3,
      }}
    >
      {children}
    </Typography>
  );
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
      {/* Page header row */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h5" fontWeight={700} color="text.primary">Dashboard</Typography>
          <Typography variant="caption" color="text.secondary">Real-time monitoring · auto-refresh every 5s</Typography>
        </Box>
        <Chip
          label={`Updated ${lastRefresh.toLocaleTimeString()}`}
          size="small"
          sx={{ bgcolor: "#1a1d2e", color: "#64748b", border: "1px solid #2d3149", fontSize: 11 }}
        />
      </Box>

      {/* ── Summary Cards ── */}
      <SectionLabel>System Overview</SectionLabel>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            label="Status" value={summary.status?.toUpperCase()}
            sub="bookshop service" icon={<MonitorHeartIcon fontSize="small" />}
            color={statusColor[summary.status] || "#6366f1"}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            label="Signals" value={summary.signals}
            sub="health checks" icon={<SignalCellularAltIcon fontSize="small" />}
            color="#6366f1"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            label="Anomalies" value={summary.anomalies}
            sub="detected events" icon={<WarningAmberIcon fontSize="small" />}
            color={summary.anomalies > 0 ? "#f59e0b" : "#22c55e"}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            label="Audits" value={summary.audits}
            sub="recovery actions" icon={<ChecklistIcon fontSize="small" />}
            color="#818cf8"
          />
        </Grid>
      </Grid>

      {/* ── MAPE-K Pipeline ── */}
      <SectionLabel>MAPE-K Pipeline</SectionLabel>
      <Paper
        sx={{
          bgcolor: "#1a1d2e",
          display: "flex",
          overflow: "hidden",
          mb: 0,
        }}
      >
        {MAPE.map((step, i) => (
          <Box
            key={step.name}
            sx={{
              flex: 1,
              px: 2,
              py: 1.5,
              borderRight: i < MAPE.length - 1 ? "1px solid #2d3149" : "none",
              display: "flex",
              flexDirection: "column",
              gap: 0.4,
              "&:hover": { bgcolor: "#1e2040" },
              transition: "background .15s",
            }}
          >
            <Box display="flex" alignItems="center" gap={1}>
              <Box
                sx={{
                  width: 8, height: 8, borderRadius: "50%",
                  bgcolor: step.color, flexShrink: 0,
                }}
              />
              <Typography variant="caption" fontWeight={700} sx={{ color: step.color, fontSize: 12, letterSpacing: "0.04em" }}>
                {step.name}
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: 11, pl: "16px" }}>
              {step.desc}
            </Typography>
          </Box>
        ))}
      </Paper>

      {/* ── Live Metrics ── */}
      <SectionLabel>Live Metrics</SectionLabel>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <MetricChart title="CPU Usage %" data={cpuData} dataKey="value" color="#6366f1" unit="%" />
        </Grid>
        <Grid item xs={12} md={6}>
          <MetricChart title="Response Time (ms)" data={rtData} dataKey="value" color="#f59e0b" unit=" ms" />
        </Grid>
      </Grid>

      {/* ── Anomaly Table ── */}
      <SectionLabel>Recent Anomalies</SectionLabel>
      <AnomalyTable rows={anomalies} />

      {/* ── Audit Table ── */}
      <SectionLabel>Recovery Audit Log</SectionLabel>
      <Box mb={4}>
        <AuditTable rows={audit} />
      </Box>
    </Box>
  );
}