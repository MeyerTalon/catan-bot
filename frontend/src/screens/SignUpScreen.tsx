import React, { useState } from "react";
import { supabase } from "../lib/supabaseClient";

type SignUpScreenProps = {
  onSwitchToLogin: () => void;
  onBack: () => void;
};

export const SignUpScreen: React.FC<SignUpScreenProps> = ({
  onSwitchToLogin,
  onBack,
}) => {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { error: signUpError } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: { username: username.trim() || undefined },
        },
      });
      if (signUpError) {
        setError(signUpError.message);
        return;
      }
      setSuccess(true);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center catan-bg">
        <div className="auth-card">
          <h1 className="auth-title">Check your email</h1>
          <p className="auth-subtitle">
            We’ve sent you a confirmation link. Click it to verify your account,
            then you can log in.
          </p>
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="landing-play-button auth-submit"
          >
            Go to log in
          </button>
        </div>
      </div>
    );
  }

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
        <h1 className="auth-title">Sign up</h1>
        <p className="auth-subtitle">Create an account with email and password.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="signup-email" className="auth-label">
            Email
          </label>
          <input
            id="signup-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="auth-input"
            placeholder="you@example.com"
            required
          />

          <label htmlFor="signup-username" className="auth-label">
            Username
          </label>
          <input
            id="signup-username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="auth-input"
            placeholder="catan_player"
          />

          <label htmlFor="signup-password" className="auth-label">
            Password
          </label>
          <input
            id="signup-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="auth-input"
            placeholder="••••••••"
            required
            minLength={6}
          />

          {error && <p className="auth-error">{error}</p>}

          <button
            type="submit"
            className="landing-play-button auth-submit"
            disabled={loading}
          >
            {loading ? "Creating account…" : "Sign up"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{" "}
          <button type="button" onClick={onSwitchToLogin} className="auth-link">
            Log in
          </button>
        </p>
      </div>
    </div>
  );
};
