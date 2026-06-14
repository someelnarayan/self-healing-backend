import { Card, CardContent, Typography } from "@mui/material";

function SummaryCard({ title, value }) {
  return (
    <Card elevation={4}>
      <CardContent>
        <Typography
          variant="h6"
          gutterBottom
        >
          {title}
        </Typography>

        <Typography
          variant="h4"
          color="primary"
        >
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default SummaryCard;