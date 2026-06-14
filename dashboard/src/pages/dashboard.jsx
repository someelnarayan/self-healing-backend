import { useEffect, useState } from "react";
import {
  Grid,
  Container,
  Typography,
  Box,
} from "@mui/material";

import SummaryCard from "../components/SummaryCard";
import api from "../services/api";

function Dashboard() {
  const [summary, setSummary] = useState({
    status: "loading",
    signals: 0,
    anomalies: 0,
    audits: 0,
  });

  const loadStatus = async () => {
    try {
      const res = await api.get("/status");

      setSummary(res.data.summary);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadStatus();

    const interval = setInterval(
      loadStatus,
      5000
    );

    return () => clearInterval(interval);
  }, []);

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Typography
          variant="h3"
          gutterBottom
        >
          Self-Healing Backend Dashboard
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <SummaryCard
              title="System Status"
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
      </Box>
    </Container>
  );
}

export default Dashboard;