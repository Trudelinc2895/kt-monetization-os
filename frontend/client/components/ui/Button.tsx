/**
 * Button — composant bouton réutilisable
 *
 * Variantes : primary | secondary | ghost | danger
 * Tailles   : sm | md | lg
 * Options   : fullWidth, loading, disabled
 *
 * Usage avec Link (Next.js) :
 *   import Link from "next/link";
 *   <Link href="/..." className={buttonVariants("primary")}>Texte</Link>
 */

import React from "react";

// ── Variants ──────────────────────────────────────────────────────────────────

const variantClasses: Record<string, string> = {
  primary:
    "bg-primary text-white hover:bg-primary-hover active:scale-[0.98] " +
    "shadow-[0_1px_3px_rgba(79,140,255,0.3)] focus-visible:ring-2 focus-visible:ring-primary/50",
  secondary:
    "border border-ui-border text-text-secondary hover:border-ui-border-strong " +
    "hover:text-text-primary bg-transparent focus-visible:ring-2 focus-visible:ring-primary/40",
  ghost:
    "text-text-secondary hover:text-text-primary hover:bg-ui-surface " +
    "bg-transparent focus-visible:ring-2 focus-visible:ring-primary/40",
  danger:
    "bg-danger text-white hover:bg-danger/90 active:scale-[0.98] " +
    "shadow-[0_1px_3px_rgba(239,68,68,0.3)] focus-visible:ring-2 focus-visible:ring-danger/50",
};

const sizeClasses: Record<string, string> = {
  sm: "h-8  px-3  text-xs  rounded-lg  gap-1.5",
  md: "h-10 px-4  text-sm  rounded-xl  gap-2",
  lg: "h-12 px-6  text-base rounded-xl  gap-2",
};

// ── buttonVariants helper — pour les Link Tailwind ────────────────────────────

export function buttonVariants(
  variant: "primary" | "secondary" | "ghost" | "danger" = "primary",
  size: "sm" | "md" | "lg" = "md",
  fullWidth = false,
): string {
  return [
    "inline-flex items-center justify-center font-semibold transition-all duration-150",
    "focus-visible:outline-none disabled:opacity-40 disabled:cursor-not-allowed",
    variantClasses[variant],
    sizeClasses[size],
    fullWidth ? "w-full" : "",
  ]
    .filter(Boolean)
    .join(" ");
}

// ── Spinner ───────────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <span
      className="inline-block w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin"
      aria-hidden="true"
    />
  );
}

// ── Button component ──────────────────────────────────────────────────────────

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
  loading?: boolean;
  children: React.ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  loading = false,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={[buttonVariants(variant, size, fullWidth), className]
        .filter(Boolean)
        .join(" ")}
    >
      {loading ? (
        <>
          <Spinner />
          <span>{children}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}

export default Button;
