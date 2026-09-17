import React, { useState } from "react";
import { CircleAlert } from "lucide-react";
import { api, apiErrorMessage } from "@/api/client";
import { AuthShell } from "@/components/auth-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setSession } from "@/lib/session";

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
      const { data, error: apiError } = await api.POST("/auth/login", {
        body: { email: email.trim(), password },
      });
      if (apiError || !data) {
        throw new Error(apiErrorMessage(apiError, "Log in failed"));
      }
      if (data.access_token) {
        setSession(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Log in failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Log in"
      description="Use the email you signed up with."
      onBack={onBack}
      footer={
        <>
          No account?
          <Button variant="link" className="px-1" onClick={onSwitchToSignUp}>
            Sign up
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="login-email">Email</Label>
          <Input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="login-password">Password</Label>
          <Input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" className="mt-2 w-full" disabled={loading}>
          {loading ? "Logging in…" : "Log in"}
        </Button>
      </form>
    </AuthShell>
  );
};
