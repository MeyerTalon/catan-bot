import React, { useState } from "react";
import { CircleAlert, CircleCheck } from "lucide-react";
import { api, apiErrorMessage } from "@/api/client";
import { AuthShell } from "@/components/auth-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type ConfirmScreenProps = {
  email: string;
  onConfirmed: () => void;
  onBack: () => void;
};

/** Enter the code Cognito emailed after sign-up; resend it if it never arrived. */
export const ConfirmScreen: React.FC<ConfirmScreenProps> = ({
  email,
  onConfirmed,
  onBack,
}) => {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      const { error: apiError } = await api.POST("/auth/confirm", {
        body: { email, code: code.trim() },
      });
      if (apiError) {
        throw new Error(apiErrorMessage(apiError, "Confirmation failed"));
      }
      onConfirmed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirmation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      const { data, error: apiError } = await api.POST(
        "/auth/resend-confirmation",
        { body: { email } },
      );
      if (apiError || !data) {
        throw new Error(apiErrorMessage(apiError, "Could not resend the code"));
      }
      setNotice(data.message);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not resend the code",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Check your email"
      description={`We sent a confirmation code to ${email}.`}
      onBack={onBack}
      footer={
        <>
          Didn’t get it?
          <Button
            variant="link"
            className="px-1"
            onClick={handleResend}
            disabled={loading}
          >
            Resend code
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="confirm-code">Confirmation code</Label>
          <Input
            id="confirm-code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="123456"
            required
            maxLength={16}
          />
        </div>

        {notice && (
          <Alert>
            <CircleCheck />
            <AlertDescription>{notice}</AlertDescription>
          </Alert>
        )}
        {error && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" className="mt-2 w-full" disabled={loading}>
          {loading ? "Confirming…" : "Confirm email"}
        </Button>
      </form>
    </AuthShell>
  );
};
