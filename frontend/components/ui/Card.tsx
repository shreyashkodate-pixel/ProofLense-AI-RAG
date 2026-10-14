import React, { forwardRef } from "react";
import styles from "./Card.module.css";

export type CardVariant = "surface" | "alt" | "muted";
export type CardPadding = "none" | "sm" | "md" | "lg";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  padding?: CardPadding;
  interactive?: boolean;
  title?: string;
  subtitle?: string;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      variant = "surface",
      padding = "md",
      interactive = false,
      title,
      subtitle,
      className,
      ...props
    },
    ref
  ) => {
    const paddingClass = {
      none: styles.padNone,
      sm: styles.padSm,
      md: styles.padMd,
      lg: styles.padLg,
    }[padding];

    const classNames = [
      styles.card,
      styles[variant],
      paddingClass,
      interactive ? styles.interactive : "",
      className || "",
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div ref={ref} className={classNames} {...props}>
        {(title || subtitle) && (
          <div className={styles.header}>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
        )}
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";
