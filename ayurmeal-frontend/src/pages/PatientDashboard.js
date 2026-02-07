import { useEffect, useState } from "react";
import axios from "axios";
import MealPlanTable from "./MealPlanTable";

export default function MyHealthPlan() {
  const [mealPlan, setMealPlan] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [mealPlanId, setMealPlanId] = useState(null);

  useEffect(() => {
    const fetchMealPlan = async () => {
      try {
        const token = localStorage.getItem("token");
        const patientId = localStorage.getItem("patient_id");

const res = await axios.get("http://localhost:8000/patients/my-plan", 
     {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        setMealPlan(res.data.meal_text);
        setMealPlanId(res.data.meal_plan_id);
      } catch (err) {
        if (err.response?.status === 404) {
          setError("Sorry, there is no meal plan generated for this number");
        } else {
          setError("Failed to load meal plan");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMealPlan();
  }, []);

  if (loading) {
    return <p>Loading your health plan...</p>;
  }

  if (error) {
    return <p style={{ color: "red" }}>{error}</p>;
  }

  return (
    <div>
      <h2 className="section-title">My Diet Plan</h2>
      {mealPlan && (
        <MealPlanTable 
          mealPlan={mealPlan} 
          mealPlanId={mealPlanId}  // Pass the ID here!
          isReadOnly={true} 
        />
      )}
    </div>
  );
}