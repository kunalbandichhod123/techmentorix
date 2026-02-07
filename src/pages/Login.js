import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { sendOtp, verifyOtp } from "../services/authService";
import "../styles/login.css";

export default function Login() {
  const navigate = useNavigate();
  
  // Shared State
  const [loading, setLoading] = useState(false);
  const [intendedRole, setIntendedRole] = useState("");

  // Patient State (Phone/OTP)
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState(1);

  // Doctor State (Email/Password)
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  
  // 🆕 Forgot Password State
  const [forgotPasswordStep, setForgotPasswordStep] = useState(0); // 0=Off, 1=Email, 2=OTP+NewPass
  const [resetOtp, setResetOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    const role = localStorage.getItem("intendedRole");
    if (!role) {
      navigate("/");
    }
    setIntendedRole(role);
  }, [navigate]);

  // ==========================================
  // 🩺 DOCTOR AUTH HANDLER
  // ==========================================
  const handleDoctorAuth = async (e) => {
    e.preventDefault();
    if (!email || !password) return alert("Please fill all fields");
    
    setLoading(true);
    const baseUrl = "http://127.0.0.1:8001"; 
    const endpoint = isRegistering 
      ? `${baseUrl}/auth/doctor/register`
      : `${baseUrl}/auth/doctor/login`;

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed");
      }

      if (isRegistering) {
        alert("Registration Successful! Please log in.");
        setIsRegistering(false);
        setPassword("");
      } else {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", "doctor");
        localStorage.setItem("userEmail", email);
        navigate("/dashboard", { replace: true });
      }

    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // 🔐 FORGOT PASSWORD HANDLERS
  // ==========================================
  
  // 1. Send OTP to Email
  const handleForgotPasswordRequest = async (e) => {
    e.preventDefault();
    if (!email) return alert("Please enter your email first.");
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:8001/auth/doctor/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to send OTP");
      
      alert(data.message);
      setForgotPasswordStep(2); // Move to OTP input
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 2. Reset Password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!resetOtp || !newPassword) return alert("Please fill all fields.");
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:8001/auth/doctor/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp: resetOtp, new_password: newPassword }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Reset failed");

      alert("Password reset successful! Please login with your new password.");
      
      // Reset State to Login View
      setForgotPasswordStep(0);
      setPassword("");
      setNewPassword("");
      setResetOtp("");
      
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // 🧘 PATIENT AUTH HANDLERS
  // ==========================================
  const handleSendOtp = async (e) => {
    e.preventDefault();
    if (!phone) return alert("Please enter phone number");
    setLoading(true);
    try {
      let formattedPhone = phone.trim();
      if (!formattedPhone.startsWith("+") && formattedPhone.length === 10) {
          formattedPhone = "+91" + formattedPhone;
      }
      await sendOtp(formattedPhone);
      setPhone(formattedPhone);
      setStep(2);
    } catch (err) {
      alert(err.message || "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await verifyOtp(phone, otp);
      if (intendedRole === "doctor") {
         alert("⛔ Doctors must use Email Login.");
         localStorage.clear();
         setLoading(false);
         return; 
      }
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("role", data.role); 
      localStorage.setItem("userPhone", phone);
      navigate("/my-plan", { replace: true });
    } catch (err) {
      alert("Verification failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    localStorage.removeItem("intendedRole");
    navigate("/");
  };

  // ==========================================
  // 🎨 RENDER
  // ==========================================
  return (
    <div className="login-page">
      <button onClick={handleBack} style={styles.backButton}>
        ⬅ Back
      </button>

      <div className="login-card">
        <h2 className="login-title">AyurMeal</h2>
        
        {/* DYNAMIC TITLE */}
        <p className="login-subtitle">
          {intendedRole === "doctor" 
            ? (forgotPasswordStep > 0 ? "Reset Password" : (isRegistering ? "Doctor Registration" : "Doctor Login"))
            : (step === 1 ? "Patient Login" : `Enter OTP sent to ${phone}`)
          }
        </p>

        {/* --- DOCTOR FLOW --- */}
        {intendedRole === "doctor" ? (
          <>
            {/* 1. FORGOT PASSWORD FLOW */}
            {forgotPasswordStep === 1 && (
               <form onSubmit={handleForgotPasswordRequest}>
                 <label className="login-label">Enter Registered Email</label>
                 <input className="login-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                 <button className="login-button" type="submit" disabled={loading}>{loading ? "Sending..." : "Send OTP"}</button>
                 <p className="resend-text" onClick={() => setForgotPasswordStep(0)} style={styles.link}>Cancel</p>
               </form>
            )}

            {forgotPasswordStep === 2 && (
               <form onSubmit={handleResetPassword}>
                 <label className="login-label">Enter OTP from Email</label>
                 <input className="login-input" value={resetOtp} onChange={(e) => setResetOtp(e.target.value)} placeholder="123456" required />
                 
                 <label className="login-label">New Password</label>
                 <input className="login-input" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="New Password" required />
                 
                 <button className="login-button" type="submit" disabled={loading}>{loading ? "Resetting..." : "Set New Password"}</button>
               </form>
            )}

            {/* 2. LOGIN / REGISTER FLOW */}
            {forgotPasswordStep === 0 && (
              <form onSubmit={handleDoctorAuth}>
                <label className="login-label">Email Address</label>
                <input
                  type="email"
                  className="login-input"
                  placeholder="doctor@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
                
                <label className="login-label">Password</label>
                <input
                  type="password"
                  className="login-input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                />

                {/* Forgot Password Link (Only in Login Mode) */}
                {!isRegistering && (
                  <div style={{textAlign: "right", marginTop: "5px"}}>
                    <span onClick={() => setForgotPasswordStep(1)} style={{...styles.link, fontSize: "12px", color: "#d32f2f"}}>
                      Forgot Password?
                    </span>
                  </div>
                )}

                <button className="login-button" type="submit" disabled={loading} style={{marginTop: '20px'}}>
                  {loading ? "Processing..." : (isRegistering ? "Register" : "Login")}
                </button>

                <p className="resend-text" onClick={() => setIsRegistering(!isRegistering)} style={styles.link}>
                  {isRegistering ? "Already have an account? Login here" : "New Doctor? Register here"}
                </p>
              </form>
            )}
          </>
        ) : (
          /* --- PATIENT FLOW (Unchanged) --- */
          <>
            {step === 1 ? (
              <form onSubmit={handleSendOtp}>
                <label className="login-label">Phone Number</label>
                <input className="login-input" placeholder="+91XXXXXXXXXX" value={phone} onChange={(e) => setPhone(e.target.value)} autoFocus />
                <button className="login-button" type="submit" disabled={loading}>{loading ? "Sending..." : "Send OTP"}</button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOtp}>
                <label className="login-label">Enter 6-Digit OTP</label>
                <input className="login-input" placeholder="123456" value={otp} onChange={(e) => setOtp(e.target.value)} autoFocus />
                <button className="login-button" type="submit" disabled={loading}>{loading ? "Verifying..." : "Verify OTP"}</button>
                <p className="resend-text" onClick={() => setStep(1)} style={styles.link}>Change Phone Number</p>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const styles = {
  backButton: {
    position: "absolute", top: "20px", left: "20px", padding: "8px 15px",
    backgroundColor: "rgba(255, 255, 255, 0.8)", color: "#4e342e",
    border: "1px solid #4e342e", borderRadius: "20px", cursor: "pointer", fontWeight: "600"
  },
  link: { cursor: "pointer", marginTop: "15px", color: "#795548", fontSize: "14px", textDecoration: "underline" }
};