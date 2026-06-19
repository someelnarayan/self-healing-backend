import { Box, CssBaseline, Toolbar } from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import theme from "./theme";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import SignalsPage from "./pages/SignalsPage";
import AnomaliesPage from "./pages/AnomaliesPage";
import AuditPage from "./pages/AuditPage";
import RecoveryPage from "./pages/RecoveryPage";
import { useEffect, useState } from "react";
import { fetchStatus } from "./services/api";
import LocalPage from "./pages/LocalPage";
import SSHPage from "./pages/SSHPage";
import PrometheusPage from "./pages/PrometheusPage";

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
              overflow: "hidden",
            }}
          >
            <Toolbar sx={{ minHeight: "64px !important" }} />
            <Box sx={{ p: 4 }}>
              <Routes>
                <Route path="/"          element={<Dashboard />} />
                <Route path="/signals"   element={<SignalsPage />} />
                <Route path="/anomalies" element={<AnomaliesPage />} />
                <Route path="/recovery"  element={<RecoveryPage />} />
                <Route path="/audit"     element={<AuditPage />} />
                <Route path="/local" element={<LocalPage />} />
                <Route path="/ssh" element={<SSHPage />} />
                <Route path="/prometheus" element={<PrometheusPage />} />
              </Routes>
            </Box>
          </Box>

        </Box>
      </BrowserRouter>
    </ThemeProvider>
  );
}
