import {
  Paper,
  Typography,
  Box,
  Chip,
  Divider,
} from "@mui/material";

import MemoryIcon from "@mui/icons-material/Memory";
import StorageIcon from "@mui/icons-material/Storage";
import DnsIcon from "@mui/icons-material/Dns";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";

export default function TargetMetricsCard({
  name,
  type,

  cpu = 0,
  ram = 0,

  response = 0,
  errors = 0,

  memory = 0,
  disk = 0,
  sshStatus = "unknown",

  health = false,
}) {
  return (
    <Paper
      sx={{
        p: 2.5,
        bgcolor: "#1a1d2e",
        border: "1px solid #2d3149",
        borderRadius: 3,
      }}
    >
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={2}
      >
        <Typography
          fontWeight={700}
          fontSize={16}
        >
          {name}
        </Typography>

        <Chip
          label={type}
          size="small"
          color="primary"
          variant="outlined"
        />
      </Box>

      <Divider sx={{ mb: 2 }} />

      <Box
        display="flex"
        flexDirection="column"
        gap={1}
      >
        <Typography variant="body2">
          CPU Usage: <b>{cpu.toFixed?.(1) ?? cpu}%</b>
        </Typography>

        <Typography variant="body2">
          RAM Usage: <b>{ram.toFixed?.(1) ?? ram}%</b>
        </Typography>

        <Typography variant="body2">
          Response: <b>{response} ms</b>
        </Typography>

        <Typography variant="body2">
          Errors: <b>{errors}</b>
        </Typography>

        {memory > 0 && (
          <Typography
            variant="body2"
            display="flex"
            alignItems="center"
            gap={1}
          >
            <MemoryIcon fontSize="small" />
            Memory: <b>{memory} MB</b>
          </Typography>
        )}

        {disk > 0 && (
          <Typography
            variant="body2"
            display="flex"
            alignItems="center"
            gap={1}
          >
            <StorageIcon fontSize="small" />
            Disk: <b>{disk}%</b>
          </Typography>
        )}

        {sshStatus !== "unknown" && (
          <Typography
            variant="body2"
            display="flex"
            alignItems="center"
            gap={1}
          >
            <DnsIcon fontSize="small" />
            SSH: <b>{sshStatus}</b>
          </Typography>
        )}

        <Box mt={1}>
          <Chip
            icon={
              health
                ? <CheckCircleIcon />
                : <ErrorIcon />
            }
            label={
              health
                ? "Healthy"
                : "Unhealthy"
            }
            color={
              health
                ? "success"
                : "error"
            }
            size="small"
          />
        </Box>
      </Box>
    </Paper>
  );
}