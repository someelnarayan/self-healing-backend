import axios from "axios";

const BASE = "http://localhost:8000";

export const fetchStatus = () => axios.get(`${BASE}/status`).then(r => r.data);
export const fetchSignals = () => axios.get(`${BASE}/signals`).then(r => r.data);
export const fetchAnomalies = () => axios.get(`${BASE}/anomalies`).then(r => r.data);
export const fetchAudit = () => axios.get(`${BASE}/audit`).then(r => r.data);

export const streamEvents = (onMessage) => {
  const es = new EventSource(`${BASE}/stream`);
  es.onmessage = (e) => onMessage(JSON.parse(e.data));
  es.onerror = () => es.close();
  return () => es.close();
};