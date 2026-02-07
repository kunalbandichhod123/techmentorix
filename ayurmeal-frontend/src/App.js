import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import RoleSelection from "./pages/RoleSelection";
import Login from "./pages/Login";
import Dashboard from "./pages/DoctorDashboard";
import MyHealthPlan from "./components/MyHealthPlan";

// A small helper to check if a user is logged in
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem("token");
  if (!token) {
    return <Navigate to="/" replace />;
  }
  return children;
};

function App() {
  return (
    <Router>
      <Routes>
        {/* Step 1: User picks Doctor or Patient */}
        <Route path="/" element={<RoleSelection />} />
        
        {/* Step 2: User enters phone and verifies OTP */}
        <Route path="/login" element={<Login />} />
        
        {/* 👇 FIX: ADD THIS ROUTE FOR PATIENTS */}
        <Route 
          path="/my-plan" 
          element={
            <ProtectedRoute>
              <MyHealthPlan />
            </ProtectedRoute>
          } 
        />

        {/* Step 3: Doctor Dashboard */}
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } 
        />

        {/* Catch-all: Send unknown paths back to start */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;