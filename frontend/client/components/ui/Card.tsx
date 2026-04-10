/**
 * Card — conteneur générique
 *
 * Variantes : outlined (bordure visible) | solid (fond surface)
 * Padding   : sm | md | lg
 */

import React from "react";

export interface CardProps {
  variant?: "outlined" | "solid";
  padding?: "sm" | "md" | "lg" | "none";
  className?: string;
  children: React.ReactNode;
}

const variantClasses: Record<string, string> = {
  outlined:
    "bg-ui-surface border border-ui-border rounded-2xl",
  solid:
    "bg-ui-elevated rounded-2xl",
};

const paddingClasses: Record<string, string> = {
  none: "",
  sm:   "p-4",
  md:   "p-6",
  lg:   "p-8",
};

export function Card({
  variant = "outlined",
  padding = "md",
  className = "",
  children,
}: CardProps) {
  return (
    <div
      className={[
        variantClasses[variant],
        paddingClasses[padding],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}

// ── Card.Header / Card.Content / Card.Footer ──────────────────────────────────

export function CardHeader({
  className = "",
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={["mb-4", className].filter(Boolean).join(" ")}>
      {children}
    </div>
  );
}

export function CardContent({
  className = "",
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={className}>{children}</div>
  );
}

export function CardFooter({
  className = "",
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={[
        "mt-4 pt-4 border-t border-ui-border",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}

export default Card;
