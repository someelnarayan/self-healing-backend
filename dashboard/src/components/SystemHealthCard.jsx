import {
  Paper,
  Typography,
  Box,
  LinearProgress,
} from "@mui/material";

export default function SystemHealthCard({
  score = 100,
}) {
  let color = "#22c55e";

  if (score < 80) color = "#f59e0b";
  if (score < 50) color = "#ef4444";

  return (
    <Paper
      sx={{
        p: 3,
        bgcolor: "#1a1d2e",
        border: "1px solid #2d3149",
      }}
    >
      <Typography
        variant="h6"
        fontWeight={700}
        gutterBottom
      >
        System Health
      </Typography>

      <Typography
        variant="h3"
        fontWeight={700}
        sx={{
          color,
          mb: 2,
        }}
      >
        {score}%
      </Typography>

      <LinearProgress
        variant="determinate"
        value={score}
        sx={{
          height: 10,
          borderRadius: 5,
        }}
      />

      <Box mt={2}>
        <Typography
          variant="caption"
          color="text.secondary"
        >
          Overall infrastructure health
        </Typography>
      </Box>
    </Paper>
  );
}