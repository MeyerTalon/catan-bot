import React, { useState } from "react";
import { supabase } from "../lib/supabaseClient";

type LoginScreenProps = {
  onSwitchToSignUp: () => void;
  onBack: () => void;
};

export const LoginScreen: React.FC<LoginScreenProps> = ({
  onSwitchToSignUp,
  onBack,
}) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });
      if (signInError) {
        setError(signInError.message);
        return;
      }
      // Success: Supabase client will persist session; parent can react to auth state if needed.
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center catan-bg">
      <div className="auth-card">
        <button
          type="button"
          onClick={onBack}
          className="auth-back"
          aria-label="Back to home"
        >
          ← Back
        </button>
        <h1 className="auth-title">Log in</h1>
        <p className="auth-subtitle">Enter your email and password.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="login-email" className="auth-label">
            Email
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="auth-input"
            placeholder="you@example.com"
            required
          />

          <label htmlFor="login-password" className="auth-label">
            Password
          </label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="auth-input"
            placeholder="••••••••"
            required
          />

          {error && <p className="auth-error">{error}</p>}

          <button
            type="submit"
            className="landing-play-button auth-submit"
            disabled={loading}
          >
            {loading ? "Signing in…" : "Log in"}
          </button>
        </form>

        <p className="auth-switch">
          Don’t have an account?{" "}
          <button type="button" onClick={onSwitchToSignUp} className="auth-link">
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
};
