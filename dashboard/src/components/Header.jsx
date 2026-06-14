import { AppBar, Toolbar, Typography, Box, Chip } from "@mui/material";
import MonitorHeartIcon from "@mui/icons-material/MonitorHeart";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";

export default function Header({ status }) {
  return (
    <AppBar position="fixed" sx={{ zIndex: 1300, bgcolor: "#1a1d2e", borderBottom: "1px solid #2d3149", boxShadow: "none" }}>
      <Toolbar sx={{ gap: 1.5 }}>
        <MonitorHeartIcon sx={{ color: "#6366f1" }} />
        <Box>
          <Typography variant="subtitle1" fontWeight={700} lineHeight={1.2}>SelfHealer Monitor</Typography>
          <Typography variant="caption" color="text.secondary">MAPE-K Autonomous Recovery System</Typography>
        </Box>
        <Box flex={1} />
        <Chip
          icon={<FiberManualRecordIcon sx={{ fontSize: "10px !important", color: status === "ok" ? "#22c55e" : "#f87171" }} />}
          label={`Live · bookshop:8000`}
          size="small"
          sx={{
            bgcolor: status === "ok" ? "#0f2d1c" : "#2d0f0f",
            color: status === "ok" ? "#4ade80" : "#f87171",
            border: `1px solid ${status === "ok" ? "#166534" : "#7f1d1d"}`,
            fontWeight: 600, fontSize: 11,
          }}
        />
      </Toolbar>
    </AppBar>
  );
}   