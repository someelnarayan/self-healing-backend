function StatusCard({ title, value }) {
  return (
    <div
      style={{
        border: "1px solid #ccc",
        padding: "15px",
        marginTop: "20px",
        borderRadius: "10px",
        width: "250px",
      }}
    >
      <h3>{title}</h3>
      <p>{value}</p>
    </div>
  );
}

export default StatusCard;