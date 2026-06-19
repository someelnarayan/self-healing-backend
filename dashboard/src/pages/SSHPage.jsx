import { useEffect, useState, useCallback } from "react";

import {
  Box,
  Typography,
  Grid,
} from "@mui/material";

import {
  fetchTargets,
  fetchSignals,
} from "../services/api";

import TargetMetricsCard from "../components/TargetMetricsCard";

export default function SSHPage() {
  const [targets, setTargets] = useState([]);
  const [signals, setSignals] = useState([]);

  const refresh = useCallback(async () => {
    try {
      const allTargets = await fetchTargets();

      const sshTargets = allTargets.filter(
        (t) => t.type === "ssh"
      );

      setTargets(sshTargets);

      const signalData = await fetchSignals(200);

      setSignals(signalData);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    refresh();

    const id = setInterval(
      refresh,
      5000
    );

    return () => clearInterval(id);
  }, [refresh]);

  const latestSignalFor = (targetName) => {
    return signals.find(
      (s) => s.target_name === targetName
    );
  };

  return (
    <Box>
      <Typography
        variant="h5"
        fontWeight={700}
        color="text.primary"
        mb={0.5}
      >
        SSH Targets
      </Typography>

      <Typography
        variant="caption"
        color="text.secondary"
        sx={{
          display: "block",
          mb: 3,
        }}
      >
        Monitoring remote servers via SSH
      </Typography>

      <Grid container spacing={2}>
        {targets.map((target) => {
          const signal = latestSignalFor(target.name);

          return (
            <Grid
              item
              xs={12}
              md={6}
              lg={4}
              key={target.name}
            >
              <TargetMetricsCard
                name={target.name}
                type={target.type}
                cpu={signal?.cpu_pct ?? 0}
                ram={signal?.ram_pct ?? 0}
                response={signal?.response_ms ?? 0}
                errors={signal?.error_count ?? 0}
                health={signal?.health_ok ?? false}
              />
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
}