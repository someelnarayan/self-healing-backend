import { Drawer, List, ListItemButton, ListItemIcon, ListItemText } from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import SignalCellularAltIcon from "@mui/icons-material/SignalCellularAlt";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import HistoryIcon from "@mui/icons-material/History";
import SecurityIcon from "@mui/icons-material/Security";
import { useNavigate, useLocation } from "react-router-dom";

const DRAWER_W = 210;

const nav = [
  { label: "Dashboard", icon: <DashboardIcon />, path: "/" },
  { label: "Signals", icon: <SignalCellularAltIcon />, path: "/signals" },
  { label: "Anomalies", icon: <WarningAmberIcon />, path: "/anomalies" },
  { label: "Recovery", icon: <SecurityIcon />, path: "/recovery" },
  { label: "Audit Log", icon: <HistoryIcon />, path: "/audit" },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <Drawer variant="permanent" sx={{
      width: DRAWER_W,
      "& .MuiDrawer-paper": { width: DRAWER_W, top: 64, bgcolor: "#1a1d2e", borderRight: "1px solid #2d3149", boxSizing: "border-box" },
    }}>
      <List sx={{ pt: 1 }}>
        {nav.map(({ label, icon, path }) => (
          <ListItemButton
            key={path}
            onClick={() => navigate(path)}
            selected={pathname === path}
            sx={{
              mx: 1, borderRadius: 2, mb: 0.5,
              "&.Mui-selected": { bgcolor: "#1e2040", color: "#818cf8", "& .MuiListItemIcon-root": { color: "#818cf8" } },
              "&:hover": { bgcolor: "#1e2040" },
            }}
          >
            <ListItemIcon sx={{ minWidth: 36, color: "#475569" }}>{icon}</ListItemIcon>
            <ListItemText primary={label} primaryTypographyProps={{ fontSize: 13, fontWeight: 500 }} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
}