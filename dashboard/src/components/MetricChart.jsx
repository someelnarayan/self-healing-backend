import { Paper, Typography, Box } from "@mui/material";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function MetricChart({ title, data, dataKey, color = "#6366f1", unit = "" }) {
  return (
    <Paper sx={{ p: 2, bgcolor: "#1a1d2e" }}>
      <Typography variant="body2" fontWeight={600} mb={2}>{title}</Typography>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3149" />
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#475569" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: "#475569" }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: "#1a1d2e", border: "1px solid #2d3149", borderRadius: 8, fontSize: 12 }}
            formatter={(v) => [`${v}${unit}`, title]}
          />
          <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} fill={`url(#grad-${dataKey})`} />
        </AreaChart>
      </ResponsiveContainer>
    </Paper>
  );
}