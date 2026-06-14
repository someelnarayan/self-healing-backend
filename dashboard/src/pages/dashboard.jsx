import StatusCard from "../components/StatusCard";

function Dashboard() {
  return (
    <div style={{ padding: "20px" }}>
      <h1>Self-Healing Backend Dashboard</h1>

      <StatusCard
        title="Service Status"
        value="HEALTHY"
      />
    </div>
  );
}

export default Dashboard;