import { describe, it, expect } from "vitest";

function hexToRgb(hex: string): [number, number, number] {
  const cleanHex = hex.replace("#", "");
  const num = parseInt(cleanHex, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((val) => {
    const s = val / 255;
    return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function getContrastRatio(hex1: string, hex2: string): number {
  const [r1, g1, b1] = hexToRgb(hex1);
  const [r2, g2, b2] = hexToRgb(hex2);
  const l1 = getLuminance(r1, g1, b1);
  const l2 = getLuminance(r2, g2, b2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("WCAG 2.1 Color Contrast Audit", () => {
  it("validates primary text on canvas exceeds WCAG AAA (7:1)", () => {
    const ratio = getContrastRatio("#202720", "#F7F7F4");
    expect(ratio).toBeGreaterThan(13.0);
  });

  it("validates primary text on white surface exceeds WCAG AAA (7:1)", () => {
    const ratio = getContrastRatio("#202720", "#FFFFFF");
    expect(ratio).toBeGreaterThan(14.0);
  });

  it("validates secondary text on canvas exceeds WCAG AA (4.5:1)", () => {
    const ratio = getContrastRatio("#58645B", "#F7F7F4");
    expect(ratio).toBeGreaterThan(5.5);
  });

  it("validates tuned tertiary text on canvas exceeds WCAG AA (4.5:1)", () => {
    const ratio = getContrastRatio("#5E6960", "#F7F7F4");
    expect(ratio).toBeGreaterThan(4.8);
  });

  it("validates white text on forest green accent exceeds WCAG AAA (7:1)", () => {
    const ratio = getContrastRatio("#FFFFFF", "#315A1B");
    expect(ratio).toBeGreaterThan(7.0);
  });

  it("validates white text on danger background exceeds WCAG AA (4.5:1)", () => {
    const ratio = getContrastRatio("#FFFFFF", "#B42318");
    expect(ratio).toBeGreaterThan(5.5);
  });

  it("validates semantic success text on soft success background exceeds WCAG AA (4.5:1)", () => {
    const ratio = getContrastRatio("#237A3B", "#EAF5EC");
    expect(ratio).toBeGreaterThan(4.5);
  });

  it("validates semantic danger text on soft danger background exceeds WCAG AA (4.5:1)", () => {
    const ratio = getContrastRatio("#B42318", "#FDECEA");
    expect(ratio).toBeGreaterThan(5.0);
  });
});
