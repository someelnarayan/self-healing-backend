import { Paper, Typography, Table, TableHead, TableRow, TableCell, TableBody, Chip } from "@mui/material";

const severityColor = { critical: "error", warning: "warning", info: "info" };

export default function AnomalyTable({ rows = [] }) {
  return (
    <Paper sx={{ bgcolor: "#1a1d2e", overflow: "hidden" }}>
      <Typography variant="body2" fontWeight={600} p={2} pb={1}>Anomaly Log</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            {["Timestamp", "Type", "Service", "Severity", "Status"].map(h => (
              <TableCell key={h}>{h}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow><TableCell colSpan={5} align="center" sx={{ color: "#475569", py: 3 }}>No anomalies recorded</TableCell></TableRow>
          ) : rows.map((r, i) => (
            <TableRow key={i} hover>
              <TableCell sx={{ color: "#94a3b8", fontSize: 12 }}>{r.timestamp}</TableCell>
              <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{r.type}</TableCell>
              <TableCell sx={{ fontSize: 12 }}>{r.service}</TableCell>
              <TableCell><Chip label={r.severity} size="small" color={severityColor[r.severity?.toLowerCase()] || "default"} /></TableCell>
              <TableCell><Chip label={r.status} size="small" color={r.status === "resolved" ? "success" : "default"} variant="outlined" /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}