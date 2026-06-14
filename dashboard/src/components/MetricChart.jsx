import { Paper, Typography, Box } from "@mui/material";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from "recharts";

export default function MetricChart({ title, data, dataKey, color = "#6366f1", unit = "" }) {
  return (
    <Paper sx={{ p: 3, bgcolor: "#1a1d2e", height: "100%" }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="body2" fontWeight={600} color="text.primary" fontSize={14}>
          {title}
        </Typography>
        <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: color, boxShadow: `0 0 6px ${color}` }} />
      </Box>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2335" vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 11, fill: "#475569" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#475569" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "#1a1d2e",
              border: "1px solid #2d3149",
              borderRadius: 8,
              fontSize: 12,
              color: "#e2e8f0",
            }}
            formatter={(v) => [`${v}${unit}`, title]}
            labelStyle={{ color: "#64748b" }}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            fill={`url(#grad-${dataKey})`}
            dot={false}
            activeDot={{ r: 4, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Paper>
  );
}