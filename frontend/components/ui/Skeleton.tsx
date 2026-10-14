import React from "react";
import styles from "./Skeleton.module.css";

export type SkeletonVariant = "text" | "rect" | "circle";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: SkeletonVariant;
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = "rect",
  width,
  height,
  className,
  style,
  ...props
}) => {
  const customStyle: React.CSSProperties = {
    ...style,
    ...(width !== undefined ? { width } : {}),
    ...(height !== undefined ? { height } : {}),
  };

  return (
    <div
      aria-hidden="true"
      className={`${styles.skeleton} ${styles[variant]} ${className || ""}`}
      style={customStyle}
      {...props}
    />
  );
};
