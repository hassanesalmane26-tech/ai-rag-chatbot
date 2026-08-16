import { useContext } from "react";
import { SessionContext } from "../context/sessionContext";

export default function useSessionContext() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSessionContext doit être utilisé dans SessionProvider");
  return value;
}
