/**
 * Badge — étiquette d'état
 *
 * Variantes : info | success | warning | danger
 * Tailles   : sm | md
 */

import React from "react";

export type BadgeVariant = "info" | "success" | "warning" | "danger";

export interface BadgeProps {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  info:    "bg-primary-muted   text-primary-strong  border border-primary/20",
  success: "bg-success-muted   text-success-text    border border-success/20",
  warning: "bg-warning-muted   text-warning-text    border border-warning/20",
  danger:  "bg-danger-muted    text-danger-text     border border-danger/20",
};

const sizeClasses: Record<string, string> = {
  sm: "px-2   py-0.5 text-xs rounded-lg",
  md: "px-2.5 py-1   text-xs rounded-xl",
};

export function Badge({
  variant = "info",
  size = "md",
  children,
  className = "",
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center font-medium",
        variantClasses[variant],
        sizeClasses[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
}

export default Badge;
