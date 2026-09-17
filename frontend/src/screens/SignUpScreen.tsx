import React, { useState } from "react";
import { CircleAlert } from "lucide-react";
import { api, apiErrorMessage } from "@/api/client";
import { AuthShell } from "@/components/auth-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setSession } from "@/lib/session";

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
      const { data, error: apiError } = await api.POST("/auth/signup", {
        body: {
          email: email.trim(),
          password,
          username: username.trim() || null,
        },
      });
      if (apiError || !data) {
        throw new Error(apiErrorMessage(apiError, "Sign up failed"));
      }
      if (data.access_token) {
        setSession(data);
      } else {
        setSuccess(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <AuthShell
        title="Check your email"
        description="We’ve sent you a confirmation link. Click it to verify your account, then log in."
      >
        <Button className="w-full" onClick={onSwitchToLogin}>
          Go to log in
        </Button>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create account"
      description="Sign up with an email and password."
      onBack={onBack}
      footer={
        <>
          Already have an account?
          <Button variant="link" className="px-1" onClick={onSwitchToLogin}>
            Log in
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="signup-email">Email</Label>
          <Input
            id="signup-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="signup-username">
            Username
            <span className="font-normal text-muted-foreground">optional</span>
          </Label>
          <Input
            id="signup-username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="catan_player"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="signup-password">Password</Label>
          <Input
            id="signup-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </div>

        {error && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" className="mt-2 w-full" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthShell>
  );
};
