import React from "react";
import { cn } from "@/lib/utils";

type HexMarkProps = React.SVGProps<SVGSVGElement>;

/** Outlined hex with a filled inner hex, drawn in the current text colour. */
export const HexMark: React.FC<HexMarkProps> = ({ className, ...props }) => (
  <svg
    viewBox="0 0 34 38"
    fill="none"
    aria-hidden="true"
    className={cn("size-9", className)}
    {...props}
  >
    <path
      d="M17 1 32 9.5v19L17 37 2 28.5v-19L17 1Z"
      stroke="currentColor"
      strokeWidth="2"
    />
    <path d="M17 8 26 13v10l-9 5-9-5V13l9-5Z" fill="currentColor" />
  </svg>
);
