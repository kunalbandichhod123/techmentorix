import { useEffect, useState } from "react";

export default function MealPlanTable({ mealPlan, patientId, isReadOnly }) {
  const [planData, setPlanData] = useState(null);
  const [activeDay, setActiveDay] = useState("Day 1");
  const [isEditing, setIsEditing] = useState(false);
  const [saved, setSaved] = useState(true);
  const [downloaded, setDownloaded] = useState(false);

  // ---------------------------------------------------------
  // 🔧 SMART PARSER (The Fix)
  // ---------------------------------------------------------
  useEffect(() => {
    if (mealPlan?.meal_text) {
      try {
        // Attempt 1: Try parsing as JSON (The Ideal Case)
        const parsed = JSON.parse(mealPlan.meal_text);
        setPlanData(parsed);
      } catch (err) {
        console.warn("JSON Parse failed, switching to Text Adapter:", err);

        // Attempt 2: Convert Plain Text Table into the Object Structure your UI needs
        const rows = mealPlan.meal_text.trim().split("\n");
        const newPlanData = {};

        rows.forEach((row, index) => {
          // Skip header row or empty lines
          if (index === 0 || !row.includes("|")) return;

          // Split columns: Day | Breakfast | Lunch | Dinner
          const cols = row.split("|").map((c) => c.trim()).filter((c) => c);
          
          if (cols.length >= 4) {
            const dayKey = cols[0].includes("Day") ? cols[0] : `Day ${index}`;
            
            newPlanData[dayKey] = {
              meals: [
                { meal: "Breakfast", opt1: cols[1], cal1: "-", opt2: "", cal2: "" },
                { meal: "Lunch",     opt1: cols[2], cal1: "-", opt2: "", cal2: "" },
                { meal: "Dinner",    opt1: cols[3], cal1: "-", opt2: "", cal2: "" },
              ],
              // Since text mode lacks these, we add placeholders so the UI doesn't crash
              workout: ["General Yoga", "30 min Walk"], 
              lifestyle: "Drink warm water throughout the day.",
              recipe: { name: "See Doctor Notes", ing: "-", ins: "-" }
            };
          }
        });

        // If conversion worked, save it; otherwise set empty
        if (Object.keys(newPlanData).length > 0) {
          setPlanData(newPlanData);
          // Update active day to the first available day
          setActiveDay(Object.keys(newPlanData)[0]);
        }
      }
      
      setIsEditing(false);
      setSaved(true);
      setDownloaded(false);
    }
  }, [mealPlan]);

  if (!planData) return <p className="loading-text">Loading your personalized plan...</p>;

  // Safety check: ensure the active day exists in data
  const days = Object.keys(planData);
  const currentDay = planData[activeDay] || planData[days[0]];

  /* ---------------- EDITING LOGIC ---------------- */
  const updateMealCell = (mealIdx, field, value) => {
    const updatedData = { ...planData };
    if (updatedData[activeDay]) {
        updatedData[activeDay].meals[mealIdx][field] = value;
        setPlanData(updatedData);
        setSaved(false);
        setDownloaded(false);
    }
  };

  /* ---------------- SAVE UPDATED PLAN ---------------- */
  const saveChanges = async () => {
    if (!patientId) {
      alert("Patient ID missing. Cannot save.");
      return;
    }

    try {
      const response = await fetch(`http://127.0.0.1:8001/patients/${patientId}/meal-plan`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`
        },
        // We save the structured data back as JSON so next time it loads perfectly
        body: JSON.stringify({ meal_text: JSON.stringify(planData) })
      });

      if (response.ok) {
        setSaved(true);
        setIsEditing(false);
        alert("Plan saved successfully!");
      } else {
        alert("Server failed to update plan.");
      }
    } catch (err) {
      alert("Failed to save changes.");
    }
  };

  /* ---------------- DOWNLOAD PDF ---------------- */
  const downloadPdf = () => {
    const planId = mealPlan?.meal_plan_id || mealPlan?.id;
    if (!planId) {
      alert("Meal Plan ID missing. Please refresh.");
      return;
    }
    window.open(`http://127.0.0.1:8001/pdf/${planId}`, "_blank");
    setDownloaded(true);
  };

  return (
    <div className="meal-plan-container fade-in">
      <h3 className="plan-title" style={{ color: "#FF5722", marginBottom: "20px" }}>
        Your 7-Day Meal & Workout Plan
      </h3>

      {/* --- DAY TABS --- */}
      <div className="tabs-container" style={{ display: "flex", justifyContent: "center", gap: "10px", marginBottom: "20px", overflowX: "auto" }}>
        {days.map((day) => (
          <button
            key={day}
            className={`tab-btn ${activeDay === day ? "active" : ""}`}
            onClick={() => setActiveDay(day)}
            style={{
                padding: "10px 20px",
                borderRadius: "20px",
                border: "1px solid #FF5722",
                backgroundColor: activeDay === day ? "#FF5722" : "white",
                color: activeDay === day ? "white" : "#FF5722",
                cursor: "pointer",
                fontWeight: "bold"
            }}
          >
            {day}
          </button>
        ))}
      </div>

      {/* --- MEAL TABLE --- */}
      {currentDay && currentDay.meals ? (
      <div className="table-wrapper">
        <table className="orange-table" style={{ width: "100%", borderCollapse: "collapse", marginBottom: "30px" }}>
          <thead>
            <tr style={{ backgroundColor: "#F5F5F5" }}>
              <th style={{ padding: "12px", border: "1px solid #ddd" }}>Meal</th>
              <th style={{ padding: "12px", border: "1px solid #ddd" }}>Option 1 Food</th>
              <th style={{ padding: "12px", border: "1px solid #ddd" }}>Calories</th>
              <th style={{ padding: "12px", border: "1px solid #ddd" }}>Option 2 Food</th>
              <th style={{ padding: "12px", border: "1px solid #ddd" }}>Calories</th>
            </tr>
          </thead>
          <tbody>
            {currentDay.meals.map((m, idx) => (
              <tr key={idx}>
                <td style={{ padding: "12px", border: "1px solid #ddd", fontWeight: "bold" }}>{m.meal}</td>
                <td 
                  contentEditable={!isReadOnly && isEditing} 
                  suppressContentEditableWarning 
                  style={{ padding: "12px", border: "1px solid #ddd", backgroundColor: isEditing ? "#FFF9C4" : "transparent" }}
                  onBlur={(e) => updateMealCell(idx, 'opt1', e.target.innerText)}
                >
                  {m.opt1}
                </td>
                <td style={{ padding: "12px", border: "1px solid #ddd" }}>{m.cal1 || "-"}</td>
                <td 
                  contentEditable={!isReadOnly && isEditing} 
                  suppressContentEditableWarning 
                  style={{ padding: "12px", border: "1px solid #ddd", backgroundColor: isEditing ? "#FFF9C4" : "transparent" }}
                  onBlur={(e) => updateMealCell(idx, 'opt2', e.target.innerText)}
                >
                  {m.opt2 || "-"}
                </td>
                <td style={{ padding: "12px", border: "1px solid #ddd" }}>{m.cal2 || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      ) : <p>No meal data for this day.</p>}

      {/* --- WORKOUT, LIFESTYLE & RECIPES --- */}
      {currentDay && (
      <div className="info-sections-container" style={{ textAlign: "left" }}>
        
        <div className="workout-section" style={{ borderLeft: "5px solid #FF5722", padding: "15px", backgroundColor: "#FFF8F1", marginBottom: "20px" }}>
          <h4 style={{ color: "#FF5722", marginTop: "0" }}>🏃 Workout Plan</h4>
          <table style={{ width: "100%", backgroundColor: "white", border: "1px solid #ddd" }}>
              <thead><tr style={{backgroundColor: "#eee"}}><th style={{textAlign: "left", padding: "8px"}}>Exercise</th></tr></thead>
              <tbody>
                {currentDay.workout && currentDay.workout.length > 0 ? (
                    currentDay.workout.map((w, i) => (
                        <tr key={i}><td style={{padding: "8px", borderBottom: "1px solid #eee"}}>{w}</td></tr>
                    ))
                ) : <tr><td style={{padding: "8px"}}>Rest Day</td></tr>}
              </tbody>
          </table>
        </div>

        <div className="lifestyle-section" style={{ borderLeft: "5px solid #FF5722", padding: "15px", backgroundColor: "#FFF8F1", marginBottom: "20px" }}>
          <h4 style={{ color: "#FF5722", marginTop: "0" }}>🌿 Lifestyle Tip</h4>
          <p style={{ backgroundColor: "white", padding: "10px", border: "1px solid #ddd" }}>{currentDay.lifestyle || "Focus on mindfulness."}</p>
        </div>

        {currentDay.recipe && (
        <div className="recipe-section" style={{ borderLeft: "5px solid #FF5722", padding: "15px", backgroundColor: "#FFF8F1" }}>
          <h4 style={{ color: "#FF5722", marginTop: "0" }}>🍲 Ayurvedic Recipe: {currentDay.recipe.name}</h4>
          <div style={{ backgroundColor: "white", padding: "15px", border: "1px solid #ddd" }}>
            <p><strong>Ingredients:</strong> {currentDay.recipe.ing}</p>
            <p><strong>Instructions:</strong> {currentDay.recipe.ins}</p>
          </div>
        </div>
        )}
      </div>
      )}

      {/* --- ACTIONS --- */}
      <div className="actions" style={{ marginTop: '30px', display: 'flex', gap: '15px', justifyContent: "center" }}>
        {!isReadOnly && (
          <>
            {!isEditing ? (
              <button className="professional-action-btn" style={{ backgroundColor: "#FF5722" }} onClick={() => setIsEditing(true)}>
                Modify Plan
              </button>
            ) : (
              <button className="professional-action-btn" style={{ backgroundColor: "#4CAF50" }} onClick={saveChanges}>
                Confirm & Save
              </button>
            )}
          </>
        )}
        
        <button 
          className="professional-action-btn" 
          style={{ backgroundColor: "#2196F3" }}
          disabled={!isReadOnly && !saved}
          onClick={downloadPdf}
        >
          {downloaded && !isReadOnly ? "PDF Downloaded" : "Download PDF"}
        </button>

        <button className="professional-action-btn" style={{ backgroundColor: "#757575" }} onClick={() => window.print()}>
          Print View
        </button>
      </div>
    </div>
  );
}