import axios from "axios";

const BASE = "http://localhost:8000";

export const fetchStatus = () => axios.get(`${BASE}/status`).then(r => r.data);

export const fetchSignals = (limit = 100) =>
  axios.get(`${BASE}/signals`, { params: { limit } }).then(r => r.data);

export const fetchAnomalies = (limit = 100) =>
  axios.get(`${BASE}/anomalies`, { params: { limit } }).then(r => r.data);

export const fetchAudit = (limit = 100) =>
  axios.get(`${BASE}/audit`, { params: { limit } }).then(r => r.data);

export const fetchRecovery = () =>
  axios.get(`${BASE}/recovery`).then(r => r.data);

export const streamEvents = (onMessage) => {
  const es = new EventSource(`${BASE}/stream`);
  es.onmessage = (e) => onMessage(JSON.parse(e.data));
  es.onerror = () => es.close();
  return () => es.close();
};