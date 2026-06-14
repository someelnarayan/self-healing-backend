import { Paper, Typography, Box } from "@mui/material";

export default function SummaryCard({ label, value, sub, icon, color = "#6366f1" }) {
  return (
    <Paper
      sx={{
        p: 2.5,
        bgcolor: "#1a1d2e",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 0.5,
      }}
    >
      <Box display="flex" justifyContent="space-between" alignItems="flex-start">
        <Typography
          variant="caption"
          sx={{ color: "#64748b", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600, fontSize: 11 }}
        >
          {label}
        </Typography>
        <Box
          sx={{
            width: 32, height: 32,
            borderRadius: "8px",
            bgcolor: `${color}18`,
            display: "flex", alignItems: "center", justifyContent: "center",
            color,
            "& svg": { fontSize: 18 },
          }}
        >
          {icon}
        </Box>
      </Box>
      <Typography
        variant="h4"
        fontWeight={700}
        sx={{ color, lineHeight: 1.1, mt: 0.5 }}
      >
        {value}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: 11 }}>
        {sub}
      </Typography>
    </Paper>
  );
}