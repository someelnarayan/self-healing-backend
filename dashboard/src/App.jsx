import { Box, CssBaseline, Toolbar } from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import theme from "./theme";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import { useEffect, useState } from "react";
import { fetchStatus } from "./services/api";

const DRAWER_W = 240;

export default function App() {
  const [status, setStatus] = useState("ok");

  useEffect(() => {
    const poll = async () => {
      try {
        const s = await fetchStatus();
        setStatus(s.summary?.status ?? s.status ?? "ok");
      } catch {}
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Header status={status} />
        <Box sx={{ display: "flex", bgcolor: "background.default", minHeight: "100vh" }}>
          <Sidebar drawerWidth={DRAWER_W} />
          <Box
            component="main"
            sx={{
              flexGrow: 1,
              width: `calc(100% - ${DRAWER_W}px)`,
              minHeight: "100vh",
              bgcolor: "#0f1117",
            }}
          >
            <Toolbar sx={{ minHeight: "64px !important" }} />
            <Box sx={{ p: 4 }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/signals" element={<PlaceholderPage title="Signals" />} />
                <Route path="/anomalies" element={<PlaceholderPage title="Anomalies" />} />
                <Route path="/recovery" element={<PlaceholderPage title="Recovery" />} />
                <Route path="/audit" element={<PlaceholderPage title="Audit Log" />} />
              </Routes>
            </Box>
          </Box>
        </Box>
      </BrowserRouter>
    </ThemeProvider>
  );
}

function PlaceholderPage({ title }) {
  return (
    <Box>
      <Box sx={{ color: "#e2e8f0", fontSize: 22, fontWeight: 700, mb: 1 }}>{title}</Box>
      <Box sx={{ color: "#475569", fontSize: 14 }}>Connect your FastAPI endpoint to populate this page.</Box>
    </Box>
  );
}