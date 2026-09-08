import "./GlowBackground.css";

/**
 * Static, low-opacity ember blobs anchored to two corners -- an echo of the
 * blurred flame-in-darkness reference imagery, kept quiet enough to sit
 * behind real content without competing with it. No motion: one deliberate
 * mood, not a scattered animated effect.
 */
export default function GlowBackground() {
  return (
    <div className="glow-bg" aria-hidden="true">
      <div className="glow-bg__blob glow-bg__blob--a" />
      <div className="glow-bg__blob glow-bg__blob--b" />
    </div>
  );
}
