import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import MealPlanTable from "../components/MealPlanTable";
import "../styles/dashboard.css";
import { logout, sendOtp } from "../services/authService";

export default function DoctorDashboard() {
  const navigate = useNavigate();

  /* ---------------- STATE ---------------- */
  const [role, setRole] = useState(""); 
  const [regStep, setRegStep] = useState(1); 
  const [otp, setOtp] = useState("");
  const [tempPhone, setTempPhone] = useState("");
  const [loading, setLoading] = useState(false);
  
  
  // Menu Dropdown State
  const [showMenu, setShowMenu] = useState(false);

  // Clinical Form State
  const [patient, setPatient] = useState({
    name: "", age: "", gender: "", height: "", weight: "",
    // Ayurvedic Params
    prakriti: "", vikriti: "", roga: "",
    agni: "", koshta: "", nadi: "", mala: "", jihva: "", bala: "", nidra: "",
    doctor_notes: ""
  });

  const [mealPlan, setMealPlan] = useState(null);
  const [showAyurveda, setShowAyurveda] = useState(true);
  
  // History State
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  /* ---------------- AUTH & LOAD LOGIC ---------------- */
  
  const fetchPatientOwnPlan = useCallback(async () => {
    if (localStorage.getItem("role") !== "patient") return;

    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8001/patients/my-plan", {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      if (res.ok) setMealPlan(await res.json());
    } catch (err) { 
      console.error(err); 
    } finally { 
      setLoading(false); 
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const userRole = localStorage.getItem("role");

    if (!token) {
      navigate("/login", { replace: true });
      return;
    }

    setRole(userRole);

    if (userRole === "doctor") {
      setMealPlan(null); // Ensure doctors start on the form
    } 
    else if (userRole === "patient") {
      fetchPatientOwnPlan();
    }
  }, [navigate, fetchPatientOwnPlan]);

  /* ---------------- ANIMATION HELPER ---------------- */
  /* ---------------- HANDLERS ---------------- */

  const handleStartVerification = async () => {
    if (!tempPhone) return alert("Enter patient phone");
    setLoading(true);
    try { 
      let formatted = tempPhone.trim();
      if (!formatted.startsWith("+")) formatted = "+91" + formatted;
      
      await sendOtp(formatted); 
      setTempPhone(formatted); 
      setRegStep(2); 
    } catch (err) { 
      alert(err.message || "Failed to send OTP"); 
    } finally { 
      setLoading(false); 
    }
  };

  const handleConfirmPatient = async () => {
    if (!otp) return alert("Enter OTP");
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8001/auth/verify-patient-registration", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: tempPhone.trim(), otp: otp.trim() })
      });
      if (res.ok) { 
       // ❌ OLD (Incorrect)
// setPatient(prev => ({ ...prev, name: tempPhone })); 

// ✅ NEW (Correct)
// 1. Save phone number to the 'phone' field
// 2. Keep 'name' empty so you can type it
setPatient(prev => ({ ...prev, phone: tempPhone, name: "" }));
        setRegStep(3); 
      } else { 
        alert("Invalid OTP"); 
      }
    } catch (err) { 
      alert("Verification error"); 
    } finally { 
      setLoading(false); 
    }
  };

  const handleChange = (e) => {
    setPatient(prev => ({ ...prev, [e.target.id]: e.target.value }));
  };

const generateMealPlan = async () => {
  setLoading(true);
  try {
    const token = localStorage.getItem("token");
    
    // FIX: Explicitly add the verified 'phone' to the payload
    const payload = {
      ...patient,
     phone: tempPhone.trim(), // Mandatory for patient identification
  age: parseInt(patient.age) || 0,// Ensure age is a number
      height: parseInt(patient.height) || 0,
      weight: parseInt(patient.weight) || 0
    };

    const pRes = await fetch("http://127.0.0.1:8001/patients", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json", 
        Authorization: `Bearer ${token}` 
      },
      body: JSON.stringify(payload)
    });
    
    if (!pRes.ok) {
      const errorDetail = await pRes.json();
      console.error("Validation Error:", errorDetail);
      throw new Error("Patient creation failed: Check console for missing fields");
    }
    
    const pData = await pRes.json();

    // Step 2: Generate the actual Meal Plan using the new patient ID
    const mRes = await fetch(`http://127.0.0.1:8001/patients/${pData.id}/meal-plan`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    });
    
    if (!mRes.ok) throw new Error("Plan generation failed");
    const mData = await mRes.json();

    setMealPlan({ ...mData, id: pData.id });
  } catch (err) { 
    alert(err.message); 
  } finally { 
    setLoading(false); 
  }
};

// Inside DoctorDashboard.js

  const loadHistory = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8001/patients/history", {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      const data = await res.json();

      // 👇 FIX: Check if data is an Array before setting it
      if (Array.isArray(data)) {
          setHistory(data);
      } else {
          console.error("API Error: Expected array but got", data);
          setHistory([]); // Fallback to empty list so app doesn't crash
      }
      
      setShowHistory(true);
      setMealPlan(null);
    } catch (err) {
      alert("Failed to load history");
      setHistory([]); // Safety net
    }
  };
  const viewDietChart = async (patientId) => {
    try {
      const res = await fetch(`http://127.0.0.1:8001/patients/${patientId}/meal-plan`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      const data = await res.json();
      setMealPlan({ ...data, id: patientId });
      setShowHistory(false);
    } catch (err) {
      alert("Failed to load chart");
    }
  };

  /* ---------------- MENU & VIEW HELPERS ---------------- */
  
  const handleMenuAction = (action) => {
    setShowMenu(false); // Close menu
    if (action === "new") {
        setMealPlan(null);
        setRegStep(1);
        setTempPhone("");
        setOtp("");
        setShowHistory(false);
        setPatient({ name: "", age: "", gender: "", height: "", weight: "", prakriti: "", vikriti: "", roga: "", agni: "", koshta: "", nadi: "", mala: "", jihva: "", bala: "", nidra: "", doctor_notes: "" });
    } else if (action === "history") {
        loadHistory();
    } else if (action === "logout") {
        logout();
        navigate("/login");
    }
  };

  const handleBackFromMealPlan = () => {
    setMealPlan(null);
    setRegStep(3); 
  };

// 👇 FIX: Use (history || []) to ensure it treats null as empty list
const filteredHistory = (history || []).filter((p) =>
    p?.name?.toLowerCase().includes(searchTerm.toLowerCase())
);

  /* --- FIX: handleDeletePatient is now INSIDE the component --- */
  const handleDeletePatient = async (id, e) => {
    e.stopPropagation(); // Prevent triggering the "View" click
    if (!window.confirm("Are you sure? This will permanently delete the Patient and their Diet Chart.")) {
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8001/patients/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      
      if (res.ok) {
        // Refresh the list immediately
        loadHistory();
      } else {
        alert("Failed to delete patient. Check console.");
      }
    } catch (err) {
      alert("Error connecting to server");
    } finally {
      setLoading(false);
    }
  };

  const handleLogoutAction = () => {
    logout(); // Calls your authService to clear tokens
    navigate("/login", { replace: true });
  }; 
  // 1. IF PATIENT: Show only their plan
// 1. IF PATIENT: Re-verified wrapper class for background consistency
  if (role === "patient") {
    return (
      <div className="dashboard-body"> {/* Background applies here */}
        <div className="header-row">
          <h2>My Health Plan</h2>
          <button className="auth-btn" style={{width: 'auto'}} onClick={handleLogoutAction}>Logout</button>
        </div>
        <div className="dashboard-form fade-in">
          {loading ? <p>Loading your plan...</p> : 
           mealPlan ? <MealPlanTable mealPlan={mealPlan} isReadOnly={true} /> : 
           <p>No plan found for your number.</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-body">

<div className="header-row">
  <h2 className="dashboard-title">
    {role === "doctor" ? "Ayurveda Doctor Dashboard" : "My Health Plan"}
  </h2>

  {role === "doctor" && (
    <div className="profile-container">
      <div
        className="doctor-profile-circle"
        onClick={() => setShowMenu(!showMenu)}
      > Dr
      </div>

{showMenu && (
  <div className="profile-dropdown">
    <button className="dropdown-item" onClick={() => handleMenuAction("new")}>
      <span>➕</span> Register New
    </button>
    {/* No extra divs or spaces here */}
    <button className="dropdown-item" onClick={() => handleMenuAction("history")}>
      <span>📜</span> Patient History
    </button>
    <button className="dropdown-item" onClick={() => handleMenuAction("logout")}>
      <span>❌</span> Logout
    </button>
  </div>
)}
            </div>
        )}
        
        {role === "patient" && <button onClick={() => { logout(); navigate("/login"); }}>Logout</button>}
      </div>

      {/* DOCTOR VIEW: Input Form */}
      {role === "doctor" && !showHistory && !mealPlan && (
        <div 
          className="dashboard-form"
          style={regStep === 3 ? { justifyContent: 'flex-start', paddingTop: '20px' } : {}}
        >
{/* DOCTOR VIEW: Step 1 & 2 Verification Card */}
{(regStep === 1 || regStep === 2) && (
  <div className="verify-page-container dashboard-verify">
    <div className="verification-card fade-in">
      {regStep === 1 ? (
        <>
          <h2 style={{ color: '#0b6e4f', marginBottom: '5px' }}>AyurMeal</h2>
          <p style={{ marginBottom: '25px' }}>verify patient details</p>

          <label style={{ display: 'block', textAlign: 'left', fontWeight: 'bold', color: '#5D4037' }}>
            Phone Number
          </label>

          <input
            className="green-input"
            placeholder="+91XXXXXXXXXX"
            value={tempPhone}
            onChange={(e) => setTempPhone(e.target.value)}
          />

          <button className="green-btn" onClick={handleStartVerification}>
            {loading ? "Sending..." : "Send OTP"}
          </button>
        </>
      ) : (
        <>
          <h3>Enter Security Code</h3>
          <p>We sent a 6-digit code to <strong>{tempPhone}</strong></p>

          <input
            className="green-input"
            placeholder="000000"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
          />

          <button className="green-btn" onClick={handleConfirmPatient}>
            {loading ? "Verifying..." : "Verify & Continue"}
          </button>

          <button className="link-btn" onClick={() => setRegStep(1)}>
            Change Phone Number
          </button>
        </>
      )}

    </div>
  </div>
)}


{regStep === 3 && (
  <div className="fade-in" style={{ width: '100%' }}>
    <h2 className="section-title">Health Details</h2>
    
    
    {/* Wrap Health Details in the same form-grid structure as Ayurveda */}
    <div className="form-grid">
      <div className="input-group">
        <label>Name</label>
        <input id="name" type="text" className="professional-input-square" placeholder="Enter full name"
value={patient.name} onChange={handleChange} />
      </div>
      <div className="input-group">
        <label>Age</label>
        <input id="age" type="number" className="professional-input-square"  placeholder="Enter age"
 value={patient.age} onChange={handleChange} />
      </div>
      <div className="input-group">
        <label>Gender</label>
        <select id="gender" className="professional-input-square"   placeholder="Select Gender"
value={patient.gender} onChange={handleChange}>
            <option value="">Select</option><option>Female</option><option>Male</option>
        </select>
      </div>
      <div className="input-group">
        <label>Height (cm)</label>
        <input id="height" className="professional-input-square"  placeholder="Enter height"
 value={patient.height} onChange={handleChange} />
      </div>
      <div className="input-group">
        <label>Weight (kg)</label>
        <input id="weight" className="professional-input-square" value={patient.weight} onChange={handleChange} />
      </div>
    </div>
<button 
  type="button" 
  className="collapsible" 
  onClick={() => setShowAyurveda(!showAyurveda)}
>
  {showAyurveda ? "Ayurvedic Parameters" : "Show Ayurvedic Parameters (Ashtavidha Pariksha)"}
</button>
    
    {showAyurveda && (
      <div className="collapsible-content">
        <h4 style={{marginTop: '10px', color: '#795548', borderBottom: '1px solid #ddd'}}>Dosha & Agni</h4>
        <div className="form-grid">
          <div className="input-group">
              <label>Prakriti (Constitution)</label>
              <select id="prakriti" className="professional-input-square" value={patient.prakriti} onChange={handleChange}>
                  <option value="">Select</option><option>Vata</option><option>Pitta</option><option>Kapha</option><option>Vata-Pitta</option><option>Pitta-Kapha</option><option>Tridosha</option>
              </select>
          </div>
                    <div className="input-group">
                        <label>Vikriti (Imbalance)</label>
                        <select id="vikriti" className="professional-input-square" value={patient.vikriti} onChange={handleChange}>
                            <option value="">Select</option><option>Vata</option><option>Pitta</option><option>Kapha</option><option>Rakta</option>
                        </select>
                    </div>
                    <div className="input-group">
                        <label>Agni (Digestion)</label>
                        <select id="agni" className="professional-input-square" value={patient.agni} onChange={handleChange}>
                            <option value="">Select</option><option>Sama</option><option>Vishama</option><option>Tikshna</option><option>Manda</option>
                        </select>
                    </div>
                    <div className="input-group">
                        <label>Koshta (Bowel)</label>
                        <select id="koshta" className="professional-input-square" value={patient.koshta} onChange={handleChange}>
                            <option value="">Select</option><option>Madhya</option><option>Krura</option><option>Mridu</option>
                        </select>
                    </div>
                  </div>

                  <h4 style={{marginTop: '15px', color: '#795548', borderBottom: '1px solid #ddd'}}>Diagnosis Details</h4>
                  <div className="form-grid">
                     <div className="input-group">
                        <label>Jihva (Tongue)</label>
                        <select id="jihva" className="professional-input-square" value={patient.jihva} onChange={handleChange}>
                            <option value="">Select</option><option>Niram (Clean)</option><option>Sama (Coated)</option><option>Dagdh (Burnt)</option>
                        </select>
                    </div>
                    <div className="input-group">
                        <label>Bala (Immunity)</label>
                        <select id="bala" className="professional-input-square" value={patient.bala} onChange={handleChange}>
                            <option value="">Select</option><option>Pravara (High)</option><option>Madhyama</option><option>Avara (Low)</option>
                        </select>
                    </div>
                    <div className="input-group">
                         <label>Nidra (Sleep)</label>
                         <select id="nidra" className="professional-input-square" value={patient.nidra} onChange={handleChange}>
                             <option value="">Select</option><option>Sound</option><option>Disturbed</option><option>Insomnia</option><option>Excessive</option>
                         </select>
                    </div>
                    <div className="input-group">
                        <label>Roga (Disease)</label>
                        <input id="roga" className="professional-input-square" placeholder="e.g. Amlapitta" value={patient.roga} onChange={handleChange} />
                    </div>
                  </div>
                  
                  <div style={{marginTop: '15px'}}>
                    <label>Doctor's Additional Notes</label>
                    <textarea 
                        id="doctor_notes" 
                        className="professional-input-square" 
                        style={{width: '100%', minHeight: '60px'}}
                        placeholder="Specific observations regarding Nadi, Mala, or lifestyle..."
                        value={patient.doctor_notes} 
                        onChange={handleChange}
                    />
                  </div>
                </div>
              )}

              <button className="professional-action-btn" onClick={generateMealPlan} disabled={loading}>
                {loading ? "Generating Plan..." : "Generate Meal Plan"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* DOCTOR VIEW: History List with Delete Option */}
      {role === "doctor" && showHistory && (
        <div className="dashboard-form fade-in" style={{ justifyContent: 'flex-start', paddingTop: '40px' }}>
           <button onClick={() => { setShowHistory(false); setRegStep(3); }} className="back-btn">⬅ Back to Form</button>
           
           <div className="card-header" style={{marginBottom: '15px', borderBottom: 'none'}}>
             <h3>Previous Patients</h3>
           </div>

           <input 
             className="professional-input-square" 
             placeholder="Search patient by name..." 
             onChange={(e) => setSearchTerm(e.target.value)} 
             style={{marginBottom: '20px'}}
           />

           <div className="history-list">
              {filteredHistory.length > 0 ? (
                filteredHistory.map(p => (
                  <div key={p.id} className="history-row" style={{
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      padding: '15px', 
                      borderBottom: '1px solid #eee'
                  }}>
                    {/* Patient Details */}
                    <div>
                      <span className="patient-name" style={{fontWeight: 'bold', color: '#5D4037', display: 'block'}}>
                        {p.name}
                      </span> 
                      <span className="patient-meta" style={{color: '#888', fontSize: '13px'}}>
                        {p.age} yrs | {p.gender}
                      </span>
                    </div>

                    {/* Action Buttons */}
                    <div style={{display: 'flex', gap: '10px'}}>
                      <button 
                        className="view-btn" 
                        onClick={() => viewDietChart(p.id)}
                        style={{
                          border: '1px solid #5D4037', 
                          background: 'transparent', 
                          color: '#5D4037', 
                          padding: '6px 15px', 
                          borderRadius: '20px', 
                          cursor: 'pointer',
                          fontWeight: '600'
                        }}
                      >
                        View
                      </button>

                      <button 
                        className="delete-btn" 
                        onClick={(e) => handleDeletePatient(p.id, e)}
                        style={{
                          border: '1px solid #ffcdd2', 
                          background: '#ffebee', 
                          color: '#c62828', 
                          padding: '6px 15px', 
                          borderRadius: '20px', 
                          cursor: 'pointer',
                          fontWeight: '600'
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <p style={{textAlign: 'center', color: '#999', marginTop: '20px'}}>No patients found.</p>
              )}
           </div>
        </div>
      )}

      {/* MEAL PLAN VIEW (Shared) */}
      {mealPlan && (
        <div className="dashboard-form fade-in" style={{ justifyContent: 'flex-start', paddingTop: '40px' }}>
          {role === "doctor" && (
            <button onClick={handleBackFromMealPlan} className="back-btn">⬅ Back </button>
          )}
          <MealPlanTable 
            mealPlan={mealPlan} 
            patientId={mealPlan.id} 
            isReadOnly={role === "patient"} 
          />
        </div>
      )}
    </div>
  );
}