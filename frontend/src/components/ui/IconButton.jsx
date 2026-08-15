export default function IconButton({ className = "", type = "button", ...props }) {
  return <button type={type} className={`ds-icon-button ${className}`.trim()} {...props} />;
}
