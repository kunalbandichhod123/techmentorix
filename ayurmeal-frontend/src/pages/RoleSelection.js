import { useNavigate } from "react-router-dom";

export default function RoleSelection() {
  const navigate = useNavigate();

  const handleSelect = (role) => {
    localStorage.setItem("intendedRole", role);
    navigate("/login");
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h2 style={styles.title}>AyurMeal</h2>
        <p style={styles.subtitle}>Please select your login type</p>

        <div style={styles.buttonGroup}>
<button
  style={styles.doctorBtn}
  onClick={() => handleSelect("doctor")}
>
  <span style={{ color: "#ffffff" }}>Doctor</span>
</button>

<button
  style={styles.patientBtn}
  onClick={() => handleSelect("patient")}
>
  <span style={{ color: "#ffffff" }}>Patient</span>
</button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "linear-gradient(135deg, #f6f1eb, #e8dccb)",
  },

  card: {
    width: "100%",
    maxWidth: "380px",
    background: "#fff",
    padding: "30px",
    borderRadius: "12px",
    boxShadow: "0 10px 30px rgba(0,0,0,0.1)",
    textAlign: "center",
  },

  title: {
    color: "#4e7c55",
    marginBottom: "5px",
  },

  subtitle: {
    fontSize: "14px",
    color: "#777",
    marginBottom: "25px",
  },

  buttonGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "15px",
  },

  doctorBtn: {
    padding: "12px",
    backgroundColor: "#4e7c55",
    color: "#ffffff",   // ✅ WHITE TEXT
    border: "none",
    borderRadius: "10px",
    cursor: "pointer",
    fontSize: "16px",
    fontWeight: "600",
  },

  patientBtn: {
    padding: "12px",
    backgroundColor: "#4e7c55",
    color: "#ffffff",   // ✅ WHITE TEXT
    border: "none",
    borderRadius: "10px",
    cursor: "pointer",
    fontSize: "16px",
    fontWeight: "600",
  },
};
