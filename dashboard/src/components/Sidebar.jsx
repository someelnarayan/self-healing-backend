import {
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
} from "@mui/material";

import DashboardIcon from "@mui/icons-material/Dashboard";
import SignalCellularAltIcon from "@mui/icons-material/SignalCellularAlt";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import HistoryIcon from "@mui/icons-material/History";
import SecurityIcon from "@mui/icons-material/Security";

import ComputerIcon from "@mui/icons-material/Computer";
import DnsIcon from "@mui/icons-material/Dns";
import StorageIcon from "@mui/icons-material/Storage";

import { useNavigate, useLocation } from "react-router-dom";

const nav = [
  {
    label: "Dashboard",
    icon: <DashboardIcon />,
    path: "/",
  },

  {
    label: "Local Targets",
    icon: <ComputerIcon />,
    path: "/local",
  },

  {
    label: "SSH Targets",
    icon: <DnsIcon />,
    path: "/ssh",
  },

  {
    label: "Prometheus",
    icon: <StorageIcon />,
    path: "/prometheus",
  },

  {
    label: "Signals",
    icon: <SignalCellularAltIcon />,
    path: "/signals",
  },

  {
    label: "Anomalies",
    icon: <WarningAmberIcon />,
    path: "/anomalies",
  },

  {
    label: "Recovery",
    icon: <SecurityIcon />,
    path: "/recovery",
  },

  {
    label: "Audit Log",
    icon: <HistoryIcon />,
    path: "/audit",
  },
];

export default function Sidebar({
  drawerWidth = 240,
}) {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,

        "& .MuiDrawer-paper": {
          width: drawerWidth,
          boxSizing: "border-box",
          bgcolor: "#1a1d2e",
          borderRight: "1px solid #2d3149",
          top: 0,
          pt: "64px",
        },
      }}
    >
      <Box sx={{ px: 2, py: 2 }}>
        <Typography
          variant="caption"
          sx={{
            color: "#334155",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            fontWeight: 600,
            fontSize: 10,
            px: 1,
          }}
        >
          Navigation
        </Typography>
      </Box>

      <List sx={{ px: 1.5, pt: 0 }}>
        {nav.map(({ label, icon, path }) => (
          <ListItemButton
            key={path}
            onClick={() => navigate(path)}
            selected={pathname === path}
            sx={{
              borderRadius: "10px",
              mb: 0.5,
              px: 1.5,
              py: 1,

              "&.Mui-selected": {
                bgcolor: "#1e2040",
                color: "#818cf8",

                "& .MuiListItemIcon-root": {
                  color: "#818cf8",
                },
              },

              "&:hover": {
                bgcolor: "#1e2040",
              },

              color: "#64748b",
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 38,
                color: "inherit",
              }}
            >
              {icon}
            </ListItemIcon>

            <ListItemText
              primary={label}
              primaryTypographyProps={{
                fontSize: 13,
                fontWeight: 500,
              }}
            />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
}