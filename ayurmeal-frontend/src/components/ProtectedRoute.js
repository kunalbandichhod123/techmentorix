// src/components/ProtectedRoute.js
import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token"); // check if JWT exists

  if (!token) {
    return <Navigate to="/login" replace />; // redirect to login if no token
  }

  return children; // render the protected page
}
