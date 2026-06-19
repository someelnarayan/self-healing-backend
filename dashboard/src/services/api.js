import axios from "axios";

const BASE = "http://localhost:8000";

// ----------------------
// System Status
// ----------------------

export const fetchStatus = () =>
  axios.get(`${BASE}/status`).then((r) => r.data);

// ----------------------
// Targets
// ----------------------

export const fetchTargets = () =>
  axios.get(`${BASE}/targets`).then((r) => r.data);

// ----------------------
// Signals
// ----------------------

export const fetchSignals = (
  limit = 100,
  target = null
) =>
  axios
    .get(`${BASE}/signals`, {
      params: {
        limit,
        target,
      },
    })
    .then((r) => r.data);

// ----------------------
// Anomalies
// ----------------------

export const fetchAnomalies = (
  limit = 100,
  target = null
) =>
  axios
    .get(`${BASE}/anomalies`, {
      params: {
        limit,
        target,
      },
    })
    .then((r) => r.data);

// ----------------------
// Audit
// ----------------------

export const fetchAudit = (
  limit = 100,
  target = null
) =>
  axios
    .get(`${BASE}/audit`, {
      params: {
        limit,
        target,
      },
    })
    .then((r) => r.data);

// ----------------------
// Recovery
// ----------------------

export const fetchRecovery = () =>
  axios.get(`${BASE}/recovery`).then((r) => r.data);

// ----------------------
// SSE Stream
// ----------------------

export const streamEvents = (onMessage) => {
  const es = new EventSource(`${BASE}/stream`);

  es.onmessage = (e) => {
    onMessage(JSON.parse(e.data));
  };

  es.onerror = () => {
    es.close();
  };

  return () => es.close();
};