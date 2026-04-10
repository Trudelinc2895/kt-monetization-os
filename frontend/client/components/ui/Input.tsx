/**
 * Input — champ de saisie unifié
 *
 * Support : label, placeholder, error, helper text, show/hide password
 */

"use client";

import React, { useState, forwardRef, useId } from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string | null;
  helperText?: string;
  containerClassName?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, helperText, containerClassName = "", className = "", type, id: idProp, ...props },
  ref,
) {
  const autoId = useId();
  const id = idProp ?? autoId;
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";
  const resolvedType = isPassword ? (showPassword ? "text" : "password") : type;

  return (
    <div className={["flex flex-col gap-1.5", containerClassName].filter(Boolean).join(" ")}>
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-text-secondary">
          {label}
        </label>
      )}

      <div className="relative">
        <input
          {...props}
          id={id}
          ref={ref}
          type={resolvedType}
          className={[
            "w-full rounded-xl px-4 py-2.5 text-sm",
            "bg-ui-elevated border transition-colors",
            "text-text-primary placeholder:text-text-muted",
            "focus:outline-none focus:ring-2",
            error
              ? "border-danger focus:ring-danger/40"
              : "border-ui-border focus:ring-primary/40 focus:border-primary",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            isPassword ? "pr-10" : "",
            className,
          ]
            .filter(Boolean)
            .join(" ")}
        />

        {isPassword && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShowPassword((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
            aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
          >
            {showPassword ? (
              // eye-off
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
                <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            ) : (
              // eye
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
            )}
          </button>
        )}
      </div>

      {error && (
        <p className="text-xs text-danger-text" role="alert">
          {error}
        </p>
      )}
      {!error && helperText && (
        <p className="text-xs text-text-muted">{helperText}</p>
      )}
    </div>
  );
});

Input.displayName = "Input";
export default Input;
