import { useEffect, useState, useCallback } from "react";

import {
  Box,
  Typography,
  Grid,
  Paper,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";

import MetricChart from "../components/MetricChart";

import {
  fetchSignals,
  fetchTargets,
} from "../services/api";

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

export default function SignalsPage() {
  const [rows, setRows] = useState([]);
  const [targets, setTargets] = useState([]);
  const [selectedTarget, setSelectedTarget] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const refresh = useCallback(async () => {
    try {
      const signalData =
        await fetchSignals(
          100,
          selectedTarget || null
        );

      setRows(signalData);

      const targetData =
        await fetchTargets();

      setTargets(targetData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedTarget]);

  useEffect(() => {
    refresh();

    const id = setInterval(
      refresh,
      5000
    );

    return () => clearInterval(id);
  }, [refresh]);

  const chronological =
    [...rows]
      .slice(0, 20)
      .reverse();

  const cpuData =
    chronological.map((r) => ({
      time: formatTime(r.ts),
      value: Math.round(
        r.cpu_pct ?? 0
      ),
    }));

  const rtData =
    chronological.map((r) => ({
      time: formatTime(r.ts),
      value: Math.round(
        r.response_ms ?? 0
      ),
    }));

  return (
    <Box>
      <Typography
        variant="h5"
        fontWeight={700}
        color="text.primary"
        mb={0.5}
      >
        Signals
      </Typography>

      <Typography
        variant="caption"
        color="text.secondary"
      >
        Raw health-check signals from the
        Monitor module · auto-refresh every
        5s
      </Typography>

      <Box mt={3} mb={2}>
        <FormControl
          size="small"
          sx={{
            minWidth: 250,
          }}
        >
          <InputLabel>
            Target
          </InputLabel>

          <Select
            value={selectedTarget}
            label="Target"
            onChange={(e) =>
              setSelectedTarget(
                e.target.value
              )
            }
          >
            <MenuItem value="">
              All Targets
            </MenuItem>

            {targets.map((t) => (
              <MenuItem
                key={t.name}
                value={t.name}
              >
                {t.name} ({t.type})
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Grid
        container
        spacing={2}
        sx={{ mt: 1 }}
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

      <Typography
        variant="caption"
        sx={{
          display: "block",
          color: "#475569",
          textTransform:
            "uppercase",
          letterSpacing:
            "0.08em",
          fontWeight: 600,
          fontSize: 11,
          mb: 1.5,
          mt: 4,
        }}
      >
        Signal Log
      </Typography>

      <Paper
        sx={{
          bgcolor: "#1a1d2e",
          overflow: "hidden",
        }}
      >
        <Table size="small">
          <TableHead>
            <TableRow>
              {[
                "Timestamp",
                "Target",
                "CPU %",
                "RAM %",
                "Response",
                "Health",
                "Errors",
              ].map((h) => (
                <TableCell key={h}>
                  {h}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>

          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  align="center"
                  sx={{
                    color:
                      "#475569",
                    py: 3,
                  }}
                >
                  {loading
                    ? "Loading signals..."
                    : "No signals found"}
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r) => (
                <TableRow
                  key={r.id}
                  hover
                >
                  <TableCell
                    sx={{
                      color:
                        "#94a3b8",
                      fontSize: 12,
                    }}
                  >
                    {formatTime(
                      r.ts
                    )}
                  </TableCell>

                  <TableCell>
                    {
                      r.target_name
                    }
                  </TableCell>

                  <TableCell>
                    {r.cpu_pct?.toFixed?.(
                      1
                    ) ??
                      r.cpu_pct}
                  </TableCell>

                  <TableCell>
                    {r.ram_pct?.toFixed?.(
                      1
                    ) ??
                      r.ram_pct}
                  </TableCell>

                  <TableCell>
                    {
                      r.response_ms
                    }
                  </TableCell>

                  <TableCell>
                    <Chip
                      label={
                        r.health_ok
                          ? "OK"
                          : "DOWN"
                      }
                      size="small"
                      color={
                        r.health_ok
                          ? "success"
                          : "error"
                      }
                      variant="outlined"
                    />
                  </TableCell>

                  <TableCell>
                    {
                      r.error_count
                    }
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}