const API_URL = "http://127.0.0.1:8001";

export async function sendOtp(phone) {
  const res = await fetch(`${API_URL}/auth/send-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to send OTP");
  }
  return res.json();
}

export async function verifyOtp(phone, otp) {
  // Ensure this URL matches your backend exactly
  const res = await fetch(`${API_URL}/auth/verify-otp`, { 
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, otp }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to verify OTP");
  }

  return await res.json();
}

export function logout() {
  localStorage.clear(); // Wipes everything to prevent stale role bugs
}