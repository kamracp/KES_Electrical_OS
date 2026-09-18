import { useLocation, useNavigate } from "react-router-dom";

// Shell back control (Master Prompt v2.1 amendment A10). Rendered once in the
// shell topbar, never per page. Hidden on Home. Goes one step back in the
// browser history; when the current page is the first entry of this session
// (router key "default" - opened directly, nothing to go back to) it falls
// back to Home instead of leaving the application.
export function BackButton() {
  const location = useLocation();
  const navigate = useNavigate();

  if (location.pathname === "/") {
    return null;
  }

  function handleBack(): void {
    if (location.key === "default") {
      void navigate("/");
      return;
    }
    void navigate(-1);
  }

  return (
    <button type="button" data-shell-back onClick={handleBack}>
      <span aria-hidden="true">←</span> Back
    </button>
  );
}
