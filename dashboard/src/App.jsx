import { Box, CssBaseline, Toolbar } from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import theme from "./theme";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import { useEffect, useState } from "react";
import { fetchStatus } from "./services/api";

const DRAWER_W = 210;

export default function App() {
  const [status, setStatus] = useState("ok");
  useEffect(() => {
    const poll = async () => {
      try { const s = await fetchStatus(); setStatus(s.summary?.status ?? s.status ?? "ok"); } catch {}
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
        <Sidebar />
        <Box component="main" sx={{ ml: `${DRAWER_W}px`, bgcolor: "background.default", minHeight: "100vh" }}>
          <Toolbar />
          <Box p={3}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/signals" element={<Box p={2} color="text.secondary">Signals page — connect /signals API</Box>} />
              <Route path="/anomalies" element={<Box p={2} color="text.secondary">Anomalies page — connect /anomalies API</Box>} />
              <Route path="/recovery" element={<Box p={2} color="text.secondary">Recovery page — connect /audit API</Box>} />
              <Route path="/audit" element={<Box p={2} color="text.secondary">Full audit log — connect /audit API</Box>} />
            </Routes>
          </Box>
        </Box>
      </BrowserRouter>
    </ThemeProvider>
  );
}