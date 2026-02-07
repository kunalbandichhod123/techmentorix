// src/components/MealPlanViewer.js
import { useEffect, useState } from "react";
import axios from "axios";
// 👇 Make sure this path is correct based on your folder structure
import MealPlanTable from "./MealPlanTable"; 

export default function MealPlanViewer() { // Renamed to match file
  const [mealPlan, setMealPlan] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [mealPlanId, setMealPlanId] = useState(null);

  useEffect(() => {
    const fetchMealPlan = async () => {
      try {
        const token = localStorage.getItem("token");
        
        // FIX: Remove 'patient_id' dependency if not needed, 
        // usually 'my-plan' endpoint uses the token to identify the user.
        
        // Ensure URL matches your backend port (usually 8000)
        const res = await axios.get("http://127.0.0.1:8001/patients/my-plan", {
             headers: {
               Authorization: `Bearer ${token}`,
             },
        });

        setMealPlan(res.data.meal_text);
        setMealPlanId(res.data.meal_plan_id);
      } catch (err) {
        if (err.response?.status === 404) {
          setError("Sorry, there is no meal plan generated for this number.");
        } else {
          setError("Failed to load meal plan. Please try again.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMealPlan();
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    window.location.href = "/";
  };

  if (loading) {
    return <div style={{textAlign: "center", marginTop: "50px"}}>Loading your health plan...</div>;
  }

  return (
    <div style={{padding: "20px"}}>
      <div style={{display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px"}}>
         <h2 className="section-title" style={{color: "#2E7D32"}}>My Diet Plan</h2>
         <button onClick={handleLogout} style={{padding: "8px 16px", background: "#d32f2f", color: "white", border: "none", borderRadius: "4px", cursor: "pointer"}}>Logout</button>
      </div>

      {error ? (
        <div style={{textAlign: "center", marginTop: "50px", color: "#d32f2f"}}>
            <h3>{error}</h3>
        </div>
      ) : (
        mealPlan && (
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