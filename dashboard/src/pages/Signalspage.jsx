import { useEffect, useState, useCallback } from "react";
import {
  Box, Typography, Grid, Paper,
  Table, TableHead, TableRow, TableCell, TableBody, Chip,
} from "@mui/material";
import MetricChart from "../components/MetricChart";
import { fetchSignals } from "../services/api";

function formatTime(ts) {
  try {
    const d = new Date(ts.endsWith("Z") ? ts : `${ts}Z`);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return ts;
  }
}

export default function SignalsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setRows(await fetchSignals(100));
    } catch {
      // keep showing previous rows on a transient network error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  // rows arrive newest-first; charts read better oldest-to-newest
  const chronological = [...rows].slice(0, 20).reverse();
  const cpuData = chronological.map((r) => ({ time: formatTime(r.ts), value: Math.round(r.cpu_pct ?? 0) }));
  const rtData = chronological.map((r) => ({ time: formatTime(r.ts), value: Math.round(r.response_ms ?? 0) }));

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} color="text.primary" mb={0.5}>
        Signals
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Raw health-check signals from the Monitor module · auto-refresh every 5s
      </Typography>

      <Grid container spacing={2} sx={{ mt: 3 }}>
        <Grid item xs={12} md={6}>
          <MetricChart title="CPU Usage %" data={cpuData} dataKey="value" color="#6366f1" unit="%" />
        </Grid>
        <Grid item xs={12} md={6}>
          <MetricChart title="Response Time (ms)" data={rtData} dataKey="value" color="#f59e0b" unit=" ms" />
        </Grid>
      </Grid>

      <Typography
        variant="caption"
        sx={{
          display: "block", color: "#475569", textTransform: "uppercase",
          letterSpacing: "0.08em", fontWeight: 600, fontSize: 11, mb: 1.5, mt: 4,
        }}
      >
        Signal Log
      </Typography>

      <Paper sx={{ bgcolor: "#1a1d2e", overflow: "hidden" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              {["Timestamp", "Service", "CPU %", "RAM %", "Response (ms)", "Health", "Errors"].map((h) => (
                <TableCell key={h}>{h}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ color: "#475569", py: 3 }}>
                  {loading ? "Loading signals…" : "No signals recorded"}
                </TableCell>
              </TableRow>
            ) : (
              rows.slice(0, 50).map((r) => (
                <TableRow key={r.id} hover>
                  <TableCell sx={{ color: "#94a3b8", fontSize: 12 }}>{formatTime(r.ts)}</TableCell>
                  <TableCell sx={{ fontSize: 12 }}>{r.target_name}</TableCell>
                  <TableCell sx={{ fontSize: 12 }}>{r.cpu_pct?.toFixed?.(1) ?? r.cpu_pct}</TableCell>
                  <TableCell sx={{ fontSize: 12 }}>{r.ram_pct?.toFixed?.(1) ?? r.ram_pct}</TableCell>
                  <TableCell sx={{ fontSize: 12 }}>{r.response_ms}</TableCell>
                  <TableCell>
                    <Chip
                      label={r.health_ok ? "OK" : "DOWN"}
                      size="small"
                      color={r.health_ok ? "success" : "error"}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell sx={{ fontSize: 12 }}>{r.error_count}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}