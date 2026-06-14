import { Paper, Typography, Box } from "@mui/material";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from "recharts";

export default function MetricChart({ title, data, dataKey, color = "#6366f1", unit = "" }) {
  return (
    <Paper
      sx={{
        p: 3,
        bgcolor: "#1a1d2e",
        border: "1px solid #2d3149",
        borderRadius: 3,
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography sx={{ fontSize: 15, fontWeight: 600, color: "#e2e8f0" }}>
          {title}
        </Typography>
        <Box sx={{
          width: 10, height: 10, borderRadius: "50%",
          bgcolor: color, flexShrink: 0,
        }} />
      </Box>

      <Box sx={{ width: "100%", height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 5, right: 16, left: -10, bottom: 0 }}
          >
            <defs>
              <linearGradient id={`grad-${dataKey}-${color}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2335" vertical={false} />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 11, fill: "#475569" }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#475569" }}
              axisLine={false}
              tickLine={false}
              width={35}
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
              cursor={{ stroke: color, strokeWidth: 1, strokeDasharray: "4 4" }}
            />
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2.5}
              fill={`url(#grad-${dataKey}-${color})`}
              dot={false}
              activeDot={{ r: 5, fill: color, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}