import { useEffect, useState, useCallback } from "react";

import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";

import AuditTable from "../components/AuditTable";

import {
  fetchAudit,
  fetchTargets,
} from "../services/api";

export default function AuditPage() {
  const [rows, setRows] = useState([]);
  const [targets, setTargets] = useState([]);
  const [selectedTarget, setSelectedTarget] =
    useState("");

  const refresh = useCallback(async () => {
    try {
      const auditData =
        await fetchAudit(
          200,
          selectedTarget || null
        );

      setRows(auditData);

      const targetData =
        await fetchTargets();

      setTargets(targetData);
    } catch (err) {
      console.error(err);
    }
  }, [selectedTarget]);

  useEffect(() => {
    refresh();

    const id = setInterval(
      refresh,
      5000
    );

    return () => clearInterval(id);
  }, [refresh]);

  return (
    <Box>
      <Typography
        variant="h5"
        fontWeight={700}
        color="text.primary"
        mb={0.5}
      >
        Audit Log
      </Typography>

      <Typography
        variant="caption"
        color="text.secondary"
        sx={{
          display: "block",
          mb: 3,
        }}
      >
        Full history of recovery actions
        executed by the Executor module ·
        auto-refresh every 5s
      </Typography>

      <Box mb={3}>
        <FormControl
          size="small"
          sx={{
            minWidth: 250,
          }}
        >
          <InputLabel>
            Target
          </InputLabel>

          <Select
            value={selectedTarget}
            label="Target"
            onChange={(e) =>
              setSelectedTarget(
                e.target.value
              )
            }
          >
            <MenuItem value="">
              All Targets
            </MenuItem>

            {targets.map((t) => (
              <MenuItem
                key={t.name}
                value={t.name}
              >
                {t.name} ({t.type})
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <AuditTable rows={rows} />
    </Box>
  );
}