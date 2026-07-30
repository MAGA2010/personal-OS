// Stage 7B-A.3.2 — Editorial corner brackets.
//
// Four L-shaped 1px lines at the corners of the central title safe
// area. Lines are intentionally short (~60px) and never form a
// closed rectangle — they read as "viewfinder brackets" rather than a
// border. Rendered as inline SVG (stroke 1px) so the file is
// resolution-independent and travels with the React tree.

export interface HeroBracketProps {
  /** Width of the bracket, in pixels. Default 280. */
  width?: number;
  /** Height of the bracket, in pixels. Default 180. */
  height?: number;
  /** Stroke alpha 0-1. Default 0.35. */
  alpha?: number;
  className?: string;
}

export function HeroBracket({
  width = 280,
  height = 180,
  alpha = 0.35,
  className = "",
}: HeroBracketProps) {
  // stroke-width 1; the L shape is 60px on each leg.
  const LEG = 60;
  // Stage 7B-A.3.3: editorial cream (#D7DCD3), not warm beige.
  // The color is one step below the title in visual weight.
  const stroke = `rgba(215, 220, 211, ${alpha})`;

  return (
    <svg
      data-testid="news-hero-bracket"
      aria-hidden="true"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className={`pointer-events-none ${className}`}
    >
      {/* Top-left */}
      <path
        d={`M 0 ${LEG} L 0 0 L ${LEG} 0`}
        stroke={stroke}
        strokeWidth={1}
        fill="none"
        strokeLinecap="square"
      />
      {/* Top-right */}
      <path
        d={`M ${width - LEG} 0 L ${width} 0 L ${width} ${LEG}`}
        stroke={stroke}
        strokeWidth={1}
        fill="none"
        strokeLinecap="square"
      />
      {/* Bottom-left */}
      <path
        d={`M 0 ${height - LEG} L 0 ${height} L ${LEG} ${height}`}
        stroke={stroke}
        strokeWidth={1}
        fill="none"
        strokeLinecap="square"
      />
      {/* Bottom-right */}
      <path
        d={`M ${width - LEG} ${height} L ${width} ${height} L ${width} ${height - LEG}`}
        stroke={stroke}
        strokeWidth={1}
        fill="none"
        strokeLinecap="square"
      />
    </svg>
  );
}

export default HeroBracket;
