import { useEffect, useState, useCallback } from "react";
import { Grid, Box, Typography, Chip, Paper } from "@mui/material";

import MonitorHeartIcon from "@mui/icons-material/MonitorHeart";
import SignalCellularAltIcon from "@mui/icons-material/SignalCellularAlt";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ChecklistIcon from "@mui/icons-material/Checklist";

import SummaryCard from "../components/SummaryCard";
import SystemHealthCard from "../components/SystemHealthCard";
import MetricChart from "../components/MetricChart";
import AnomalyTable from "../components/AnomalyTable";
import AuditTable from "../components/AuditTable";

import {
  fetchStatus,
  fetchAnomalies,
  fetchAudit,
  fetchSignals,
  fetchTargets,
} from "../services/api";

const MAPE = [
  {
    name: "Monitor",
    desc: "Health checks & metrics",
    color: "#6366f1",
  },
  {
    name: "Analyze",
    desc: "Root cause detection",
    color: "#818cf8",
  },
  {
    name: "Plan",
    desc: "Recovery strategy",
    color: "#a5b4fc",
  },
  {
    name: "Execute",
    desc: "Automated recovery",
    color: "#f59e0b",
  },
  {
    name: "Knowledge",
    desc: "SQLite audit store",
    color: "#22c55e",
  },
];

function formatTime(ts) {
  try {
    const d = new Date(
      ts.endsWith("Z")
        ? ts
        : `${ts}Z`
    );

    return d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
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
  const [summary, setSummary] = useState({
    status: "ok",
    signals: 0,
    anomalies: 0,
    audits: 0,
  });

  const [targets, setTargets] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [audit, setAudit] = useState([]);

  const [cpuData, setCpuData] = useState([]);
  const [rtData, setRtData] = useState([]);

  const [lastRefresh, setLastRefresh] =
    useState(new Date());

  const refresh = useCallback(async () => {
    try {
      const s = await fetchStatus();
      setSummary(s.summary ?? s);
    } catch {}

    try {
      const targetData =
        await fetchTargets();

      setTargets(targetData);
    } catch {}

    try {
      const anomalyData =
        await fetchAnomalies();

      setAnomalies(anomalyData);
    } catch {}

    try {
      const auditData =
        await fetchAudit();

      setAudit(auditData);
    } catch {}

    try {
      const signals =
        await fetchSignals(50);

      const chronological =
        [...signals]
          .slice(0, 14)
          .reverse();

      setCpuData(
        chronological.map((r) => ({
          time: formatTime(r.ts),
          value: Math.round(
            r.cpu_pct ?? 0
          ),
        }))
      );

      setRtData(
        chronological.map((r) => ({
          time: formatTime(r.ts),
          value: Math.round(
            r.response_ms ?? 0
          ),
        }))
      );
    } catch {}

    setLastRefresh(new Date());
  }, []);

  useEffect(() => {
    refresh();

    const id = setInterval(
      refresh,
      5000
    );

    return () =>
      clearInterval(id);
  }, [refresh]);

  const totalTargets =
    targets.length;

  const localTargets =
    targets.filter(
      (t) => t.type === "local"
    ).length;

  const sshTargets =
    targets.filter(
      (t) => t.type === "ssh"
    ).length;

  const prometheusTargets =
    targets.filter(
      (t) =>
        t.type === "prometheus"
    ).length;

  const healthScore =
    totalTargets === 0
      ? 100
      : Math.max(
          0,
          Math.round(
            ((totalTargets -
              summary.anomalies) /
              totalTargets) *
              100
          )
        );

  return (
    <Box>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Box>
          <Typography
            variant="h5"
            fontWeight={700}
            color="text.primary"
          >
            Dashboard
          </Typography>

          <Typography
            variant="caption"
            color="text.secondary"
          >
            Multi-target monitoring
            platform · auto-refresh
            every 5s
          </Typography>
        </Box>

        <Chip
          label={`Updated ${lastRefresh.toLocaleTimeString()}`}
          size="small"
          sx={{
            bgcolor: "#1a1d2e",
            color: "#64748b",
            border:
              "1px solid #2d3149",
            fontSize: 11,
          }}
        />
      </Box>

      <SectionLabel>
        System Overview
      </SectionLabel>

      <Grid
        container
        spacing={2}
      >
        <Grid
          item
          xs={12}
          sm={6}
          md={3}
        >
          <SummaryCard
            label="Targets"
            value={totalTargets}
            sub="configured targets"
            icon={
              <MonitorHeartIcon fontSize="small" />
            }
            color="#22c55e"
          />
        </Grid>

        <Grid
          item
          xs={12}
          sm={6}
          md={3}
        >
          <SummaryCard
            label="Local"
            value={localTargets}
            sub="local services"
            icon={
              <SignalCellularAltIcon fontSize="small" />
            }
            color="#6366f1"
          />
        </Grid>

        <Grid
          item
          xs={12}
          sm={6}
          md={3}
        >
          <SummaryCard
            label="SSH"
            value={sshTargets}
            sub="remote servers"
            icon={
              <WarningAmberIcon fontSize="small" />
            }
            color="#f59e0b"
          />
        </Grid>

        <Grid
          item
          xs={12}
          sm={6}
          md={3}
        >
          <SummaryCard
            label="Prometheus"
            value={prometheusTargets}
            sub="metrics targets"
            icon={
              <ChecklistIcon fontSize="small" />
            }
            color="#818cf8"
          />
        </Grid>
      </Grid>

      <SectionLabel>
        System Health
      </SectionLabel>

      <SystemHealthCard
        score={healthScore}
      />

      <SectionLabel>
        MAPE-K Pipeline
      </SectionLabel>

      <Paper
        sx={{
          bgcolor: "#1a1d2e",
          display: "flex",
          overflow: "hidden",
        }}
      >
        {MAPE.map(
          (step, i) => (
            <Box
              key={step.name}
              sx={{
                flex: 1,
                px: 2,
                py: 1.5,
                borderRight:
                  i <
                  MAPE.length - 1
                    ? "1px solid #2d3149"
                    : "none",
              }}
            >
              <Typography
                variant="caption"
                fontWeight={700}
                sx={{
                  color:
                    step.color,
                }}
              >
                {step.name}
              </Typography>

              <Typography
                variant="caption"
                display="block"
                color="text.secondary"
              >
                {step.desc}
              </Typography>
            </Box>
          )
        )}
      </Paper>

      <SectionLabel>
        Live Metrics
      </SectionLabel>

      <Grid
        container
        spacing={2}
      >
        <Grid
          item
          xs={12}
          md={6}
        >
          <MetricChart
            title="CPU Usage %"
            data={cpuData}
            dataKey="value"
            color="#6366f1"
            unit="%"
          />
        </Grid>

        <Grid
          item
          xs={12}
          md={6}
        >
          <MetricChart
            title="Response Time (ms)"
            data={rtData}
            dataKey="value"
            color="#f59e0b"
            unit=" ms"
          />
        </Grid>
      </Grid>

      <SectionLabel>
        Recent Anomalies
      </SectionLabel>

      <AnomalyTable
        rows={anomalies}
      />

      <SectionLabel>
        Recovery Audit Log
      </SectionLabel>

      <Box mb={4}>
        <AuditTable
          rows={audit}
        />
      </Box>
    </Box>
  );
}