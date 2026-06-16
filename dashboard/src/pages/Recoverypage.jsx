import { useEffect, useState, useCallback } from "react";
import { Box, Typography, Grid, Paper, Chip, LinearProgress } from "@mui/material";
import ShieldIcon from "@mui/icons-material/Shield";
import AuditTable from "../components/AuditTable";
import { fetchRecovery, fetchAudit } from "../services/api";

const COOLDOWN_SECONDS = 30; // matches kb.set_cooldown(target.name, 30) in main.py

export default function RecoveryPage() {
  const [targets, setTargets] = useState([]);
  const [recentAudits, setRecentAudits] = useState([]);

  const refresh = useCallback(async () => {
    try {
      setTargets(await fetchRecovery());
    } catch {
      // keep previous values on a transient network error
    }
    try {
      setRecentAudits(await fetchAudit(50));
    } catch {}
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} color="text.primary" mb={0.5}>
        Recovery
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 3 }}>
        Cooldown status per service · auto-refresh every 5s
      </Typography>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        {targets.length === 0 ? (
          <Grid item xs={12}>
            <Paper sx={{ bgcolor: "#1a1d2e", p: 3, textAlign: "center", color: "#475569" }}>
              No targets configured
            </Paper>
          </Grid>
        ) : (
          targets.map((t) => (
            <Grid item xs={12} sm={6} md={4} key={t.target}>
              <Paper sx={{ bgcolor: "#1a1d2e", p: 2.5 }}>
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <ShieldIcon fontSize="small" sx={{ color: t.on_cooldown ? "#f59e0b" : "#22c55e" }} />
                    <Typography fontWeight={600} fontSize={14}>{t.target}</Typography>
                  </Box>
                  <Chip
                    label={t.on_cooldown ? "Cooldown" : "Ready"}
                    size="small"
                    color={t.on_cooldown ? "warning" : "success"}
                    variant="outlined"
                  />
                </Box>

                {t.on_cooldown && (
                  <>
                    <LinearProgress
                      variant="determinate"
                      value={Math.max(0, 100 - (t.cooldown_remaining / COOLDOWN_SECONDS) * 100)}
                      sx={{ height: 6, borderRadius: 3, bgcolor: "#2d3149", mb: 0.5 }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {t.cooldown_remaining}s remaining
                    </Typography>
                  </>
                )}
              </Paper>
            </Grid>
          ))
        )}
      </Grid>

      <Typography
        variant="caption"
        sx={{
          display: "block", color: "#475569", textTransform: "uppercase",
          letterSpacing: "0.08em", fontWeight: 600, fontSize: 11, mb: 1.5,
        }}
      >
        Recent Recovery Actions
      </Typography>
      <AuditTable rows={recentAudits} />
    </Box>
  );
}