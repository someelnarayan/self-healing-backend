import { useEffect, useState, useCallback } from "react";
import { Box, Typography } from "@mui/material";
import AnomalyTable from "../components/AnomalyTable";
import { fetchAnomalies } from "../services/api";

export default function AnomaliesPage() {
  const [rows, setRows] = useState([]);

  const refresh = useCallback(async () => {
    try {
      setRows(await fetchAnomalies(200));
    } catch {
      // keep previous rows on a transient network error
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} color="text.primary" mb={0.5}>
        Anomalies
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 3 }}>
        All anomalies detected by the Analyzer module · auto-refresh every 5s
      </Typography>
      <AnomalyTable rows={rows} />
    </Box>
  );
}