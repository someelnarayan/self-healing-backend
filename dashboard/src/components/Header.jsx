import { Typography, Box } from "@mui/material";

export default function Header() {
  return (
    <Box mb={4}>
      <Typography
        variant="h4"
        fontWeight="bold"
      >
        Self-Healing Backend System
      </Typography>

      <Typography color="text.secondary">
        Real-Time Monitoring Dashboard
      </Typography>
    </Box>
  );
}