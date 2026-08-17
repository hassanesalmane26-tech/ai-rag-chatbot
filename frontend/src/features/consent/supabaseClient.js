import { createClient } from "@supabase/supabase-js";
import { consentConfiguration } from "./consentState";

const configured = consentConfiguration(
  import.meta.env.VITE_SUPABASE_PROJECT_URL || "",
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "",
);

let client;

export function consentClient() {
  if (!configured.enabled) return null;
  if (!client) {
    client = createClient(configured.projectUrl, import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
    });
  }
  return client;
}
