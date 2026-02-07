import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function PatientInputForm() {
  const navigate = useNavigate();
  const [patient, setPatient] = useState({
    name: "",
    age: "",
    gender: "",
    height: "",
    weight: "",
  });

  const handleChange = (e) =>
    setPatient({ ...patient, [e.target.name]: e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();

    // Here you can send patient data to backend
    console.log("Patient data:", patient);

    // After saving data, redirect to dashboard
    navigate("/dashboard");
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>Patient Input Form</h2>
      <form onSubmit={handleSubmit}>
        <label>Name</label>
        <input name="name" value={patient.name} onChange={handleChange} />

        <label>Age</label>
        <input
          name="age"
          type="number"
          value={patient.age}
          onChange={handleChange}
        />

        <label>Gender</label>
        <select name="gender" value={patient.gender} onChange={handleChange}>
          <option value="">Select</option>
          <option>Female</option>
          <option>Male</option>
          <option>Other</option>
        </select>

        <label>Height (cm)</label>
        <input name="height" value={patient.height} onChange={handleChange} />

        <label>Weight (kg)</label>
        <input name="weight" value={patient.weight} onChange={handleChange} />

        <button type="submit">Submit</button>
      </form>
    </div>
  );
}
