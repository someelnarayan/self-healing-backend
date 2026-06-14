import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "dark",
    background: { default: "#0f1117", paper: "#1a1d2e" },
    primary: { main: "#6366f1" },
    success: { main: "#22c55e" },
    warning: { main: "#f59e0b" },
    error: { main: "#f87171" },
    text: { primary: "#e2e8f0", secondary: "#64748b" },
    divider: "#2d3149",
  },
  typography: {
    fontFamily: "'Inter', 'system-ui', sans-serif",
    h6: { fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: "none", border: "1px solid #2d3149" },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: "#1e2335" },
        head: { color: "#475569", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" },
      },
    },
  },
});

export default theme;