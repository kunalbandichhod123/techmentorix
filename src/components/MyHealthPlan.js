// src/components/MyHealthPlan.js
import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom"; // Added for logout redirect
import MealPlanTable from "./MealPlanTable"; // Ensure this file exists in components too

export default function MyHealthPlan() {
  const [mealPlan, setMealPlan] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [mealPlanId, setMealPlanId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchMealPlan = async () => {
      try {
        const token = localStorage.getItem("token");
        
        // Use the new endpoint that relies on the token, not patient_id
        const res = await axios.get("http://127.0.0.1:8001/patients/my-plan", {
             headers: {
               Authorization: `Bearer ${token}`,
             },
        });

        // The backend returns { meal_text: "...", meal_plan_id: ... }
        setMealPlan(res.data.meal_text);
        setMealPlanId(res.data.meal_plan_id);
      } catch (err) {
        if (err.response?.status === 404) {
          setError("No meal plan found. Please ask your doctor to generate one.");
        } else {
          setError("Failed to load meal plan. Please try again later.");
          console.error(err);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMealPlan();
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  if (loading) {
    return <div style={{textAlign: "center", padding: "50px"}}>Loading your health plan...</div>;
  }

  return (
    <div className="dashboard-body" style={{ minHeight: "100vh", padding: "20px" }}>
      <div className="header-row" style={{display: "flex", justifyContent: "space-between", marginBottom: "20px"}}>
         <h2 style={{color: "#2E7D32"}}>My Diet Plan</h2>
         <button 
            onClick={handleLogout} 
            style={{padding: "8px 16px", background: "#d32f2f", color: "white", border: "none", borderRadius: "4px", cursor: "pointer"}}
         >
            Logout
         </button>
      </div>

      {error ? (
        <div style={{textAlign: "center", marginTop: "50px", color: "#d32f2f"}}>
            <h3>{error}</h3>
        </div>
      ) : (
        mealPlan && (
            // Pass the data to your Table component
            <MealPlanTable 
                mealPlan={{ meal_text: mealPlan, id: mealPlanId }} 
                patientId={mealPlanId}  
                isReadOnly={true} 
            />
        )
      )}
    </div>
  );
}