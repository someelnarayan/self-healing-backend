import { Card, CardContent, Typography } from "@mui/material";

export default function SummaryCard({
  title,
  value,
}) {
  return (
    <Card elevation={4}>
      <CardContent>
        <Typography
          color="text.secondary"
          gutterBottom
        >
          {title}
        </Typography>

        <Typography
          variant="h4"
          fontWeight="bold"
        >
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}