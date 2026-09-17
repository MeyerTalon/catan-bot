import React from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type AuthShellProps = {
  title: string;
  description: string;
  onBack?: () => void;
  footer?: React.ReactNode;
  children: React.ReactNode;
};

/** Centered card used by the login, sign-up, and confirmation screens. */
export const AuthShell: React.FC<AuthShellProps> = ({
  title,
  description,
  onBack,
  footer,
  children,
}) => (
  <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-4 py-10">
    <div className="w-full max-w-sm">
      {onBack && (
        <Button variant="ghost" size="sm" onClick={onBack} className="-ml-2">
          <ArrowLeft data-icon="inline-start" />
          Back
        </Button>
      )}
    </div>
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-xl">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
      {footer && (
        <CardFooter className="justify-center text-sm text-muted-foreground">
          {footer}
        </CardFooter>
      )}
    </Card>
  </div>
);
