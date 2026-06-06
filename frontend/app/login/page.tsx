"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

function getApiUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL;
  if (configuredUrl) return configuredUrl;
  if (typeof window !== "undefined" && window.location.hostname.endsWith(".up.railway.app")) {
    return "https://astonachikw-production.up.railway.app";
  }
  return "http://127.0.0.1:8000";
}

const API_URL = getApiUrl();
const DEMO_EMAIL = "demo@astrocycle.local";
const DEMO_PASSWORD = "demo12345";
const USERS_KEY = "astrocycle_local_users";

type LocalUser = {
  email: string;
  password: string;
};

function readLocalUsers(): LocalUser[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY) ?? "[]") as LocalUser[];
  } catch {
    return [];
  }
}

function writeLocalUsers(users: LocalUser[]) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function setSession(email: string, source: "api" | "local") {
  localStorage.setItem("astrocycle_token", `${source}-token-${Date.now()}`);
  localStorage.setItem("astrocycle_user", email);
}

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function tryApiLogin() {
    const formData = new URLSearchParams();
    formData.append("grant_type", "password");
    formData.append("username", email);
    formData.append("password", password);

    const response = await fetch(`${API_URL}/v1/auth/login`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) return false;

    const data = await response.json();
    localStorage.setItem("astrocycle_token", data.access_token);
    localStorage.setItem("astrocycle_user", email);
    return true;
  }

  async function tryApiSignup() {
    const response = await fetch(`${API_URL}/v1/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    return response.ok;
  }

  function loginLocally() {
    const normalizedEmail = email.trim().toLowerCase();
    const users = readLocalUsers();
    const demoMatch = normalizedEmail === DEMO_EMAIL && password === DEMO_PASSWORD;
    const userMatch = users.some((user) => user.email === normalizedEmail && user.password === password);

    if (!demoMatch && !userMatch) {
      setError("Akun tidak ditemukan. Pakai akun demo atau buat akun lokal dulu.");
      return false;
    }

    setSession(normalizedEmail, "local");
    return true;
  }

  function signupLocally() {
    const normalizedEmail = email.trim().toLowerCase();
    const users = readLocalUsers();
    if (users.some((user) => user.email === normalizedEmail)) {
      setError("Email lokal sudah terdaftar. Silakan login.");
      return false;
    }

    writeLocalUsers([...users, { email: normalizedEmail, password }]);
    setSession(normalizedEmail, "local");
    return true;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setStatus("");
    setSubmitting(true);

    try {
      if (mode === "signup") {
        try {
          await tryApiSignup();
        } catch {
          // Backend bersifat opsional saat memakai mode demo lokal.
        }

        if (signupLocally()) {
          router.push("/dashboard");
        }
        return;
      }

      try {
        if (await tryApiLogin()) {
          router.push("/dashboard");
          return;
        }
      } catch {
        setStatus("Backend belum aktif, mencoba login lokal.");
      }

      if (loginLocally()) {
        router.push("/dashboard");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-card__header">
          <p>Akses AstroCycle</p>
          <h1>{mode === "login" ? "Masuk" : "Buat Akun"}</h1>
        </div>

        <div className="auth-tabs" aria-label="Authentication mode">
          <button className={mode === "login" ? "active" : ""} type="button" onClick={() => setMode("login")}>
            Masuk
          </button>
          <button className={mode === "signup" ? "active" : ""} type="button" onClick={() => setMode("signup")}>
            Daftar
          </button>
        </div>

        <form onSubmit={handleSubmit} className="grid">
          <label>
            Email
            <input
              className="input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Kata Sandi
            <input
              className="input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={6}
              required
            />
          </label>

          <div className="demo-credential">
            <strong>Akun demo:</strong> {DEMO_EMAIL} / {DEMO_PASSWORD}
          </div>

          {status ? <p className="form-status">{status}</p> : null}
          {error ? <p className="form-error">{error}</p> : null}

          <button className="button" type="submit" disabled={submitting}>
            {submitting ? "Memproses..." : mode === "login" ? "Masuk" : "Buat Akun"}
          </button>
        </form>
      </section>
    </main>
  );
}
