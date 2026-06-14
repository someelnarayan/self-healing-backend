import { useEffect, useState } from "react";

import {
  Grid,
  Box,
  Paper,
  Typography,
} from "@mui/material";

import SummaryCard from "../components/SummaryCard";
import Header from "../components/Header";

import api from "../services/api";

export default function Dashboard() {
  const [summary, setSummary] = useState({
    status: "loading",
    signals: 0,
    anomalies: 0,
    audits: 0,
  });

  useEffect(() => {
    loadStatus();

    const interval = setInterval(
      loadStatus,
      5000
    );

    return () => clearInterval(interval);
  }, []);

  async function loadStatus() {
    try {
      const res = await api.get("/status");

      setSummary(res.data.summary);
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <Box p={4}>
      <Header />

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <SummaryCard
            title="Status"
            value={summary.status}
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <SummaryCard
            title="Signals"
            value={summary.signals}
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <SummaryCard
            title="Anomalies"
            value={summary.anomalies}
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <SummaryCard
            title="Audits"
            value={summary.audits}
          />
        </Grid>
      </Grid>

      <Paper
        sx={{
          mt: 4,
          p: 3,
        }}
      >
        <Typography variant="h6">
          System Overview
        </Typography>

        <Typography mt={2}>
          Monitoring Bookshop Service
        </Typography>

        <Typography>
          MAPE-K Loop Active
        </Typography>

        <Typography>
          Auto Recovery Enabled
        </Typography>
      </Paper>
    </Box>
  );
}