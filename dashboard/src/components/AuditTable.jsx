import { Paper, Typography, Table, TableHead, TableRow, TableCell, TableBody, Chip, Avatar, Box } from "@mui/material";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import NotificationsIcon from "@mui/icons-material/Notifications";
import RepeatIcon from "@mui/icons-material/Repeat";

const actionIcon = {
  restart_service: <RestartAltIcon fontSize="small" />,
  send_alert: <NotificationsIcon fontSize="small" />,
  retry_http_endpoint: <RepeatIcon fontSize="small" />,
};
const actionColor = { restart_service: "#6366f1", send_alert: "#f59e0b", retry_http_endpoint: "#22c55e" };

export default function AuditTable({ rows = [] }) {
  return (
    <Paper sx={{ bgcolor: "#1a1d2e", overflow: "hidden" }}>
      <Typography variant="body2" fontWeight={600} p={2} pb={1}>Recovery Audit Log</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            {["Timestamp", "Action", "Target", "Result"].map(h => (
              <TableCell key={h}>{h}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow><TableCell colSpan={4} align="center" sx={{ color: "#475569", py: 3 }}>No audit records yet</TableCell></TableRow>
          ) : rows.map((r, i) => (
            <TableRow key={i} hover>
              <TableCell sx={{ color: "#94a3b8", fontSize: 12 }}>{r.timestamp}</TableCell>
              <TableCell>
                <Box display="flex" alignItems="center" gap={1}>
                  <Avatar sx={{ width: 24, height: 24, bgcolor: `${actionColor[r.action]}22`, color: actionColor[r.action] }}>
                    {actionIcon[r.action] || <RestartAltIcon fontSize="small" />}
                  </Avatar>
                  <Typography variant="caption" fontFamily="monospace">{r.action}</Typography>
                </Box>
              </TableCell>
              <TableCell sx={{ fontSize: 12 }}>{r.target}</TableCell>
              <TableCell><Chip label={r.result} size="small" color={r.result === "success" ? "success" : "error"} /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}