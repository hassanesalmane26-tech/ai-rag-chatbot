export default function Button({ className = "", variant = "primary", type = "button", ...props }) {
  const variantClass = variant === "secondary" ? "ds-button--secondary" : "";
  return <button type={type} className={`ds-button ${variantClass} ${className}`.trim()} {...props} />;
}
