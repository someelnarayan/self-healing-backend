import { Paper, Typography, Box } from "@mui/material";

export default function SummaryCard({ label, value, sub, icon, color = "#6366f1" }) {
  return (
    <Paper sx={{ p: 2, bgcolor: "#1a1d2e" }}>
      <Box display="flex" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography variant="caption" color="text.secondary" textTransform="uppercase" letterSpacing="0.06em">
            {label}
          </Typography>
          <Typography variant="h4" fontWeight={700} sx={{ color, mt: 0.5, lineHeight: 1 }}>
            {value}
          </Typography>
          {sub && <Typography variant="caption" color="text.secondary" mt={0.5}>{sub}</Typography>}
        </Box>
        <Box sx={{ p: 1, bgcolor: `${color}22`, borderRadius: 2, color }}>
          {icon}
        </Box>
      </Box>
    </Paper>
  );
}