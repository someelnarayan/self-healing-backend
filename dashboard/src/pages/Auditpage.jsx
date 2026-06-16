import { useEffect, useState, useCallback } from "react";
import { Box, Typography } from "@mui/material";
import AuditTable from "../components/AuditTable";
import { fetchAudit } from "../services/api";

export default function AuditPage() {
  const [rows, setRows] = useState([]);

  const refresh = useCallback(async () => {
    try {
      setRows(await fetchAudit(200));
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
        Audit Log
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 3 }}>
        Full history of recovery actions executed by the Executor module · auto-refresh every 5s
      </Typography>
      <AuditTable rows={rows} />
    </Box>
  );
}