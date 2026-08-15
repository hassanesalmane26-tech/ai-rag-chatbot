export default function TridentMark({ className = "", label = "TRIDENT" }) {
  return (
    <span className={`trident-mark ${className}`.trim()} role="img" aria-label={label}>
      <svg className="trident-mark__core" viewBox="0 0 32 36" aria-hidden="true">
        <path className="trident-mark__outline" d="M16 33V5M16 10 9 3v10M16 10l7-7v10M8 17h16M11 33h10" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.35" />
        <path className="trident-mark__spark" d="M16 7v22M10 16h12" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="0.75" />
        <circle cx="16" cy="17" r="1.75" fill="currentColor" />
      </svg>
      <span className="trident-mark__aura" />
    </span>
  );
}
