export function consentConfiguration(projectUrl, publishableKey) {
  try {
    const url = new URL(projectUrl);
    const validOrigin = url.protocol === "https:" && url.pathname.replaceAll("/", "") === "";
    const invalidKeyCharacter = ["[", "]", "<", ">"].some((item) => publishableKey?.includes(item));
    const validKey = typeof publishableKey === "string"
      && publishableKey.startsWith("sb_publishable_")
      && !invalidKeyCharacter
      && !/\s/.test(publishableKey);
    return { enabled: validOrigin && validKey, projectUrl: url.origin };
  } catch {
    return { enabled: false, projectUrl: "" };
  }
}

export function authorizationId(search) {
  const value = new URLSearchParams(search).get("authorization_id")?.trim() || "";
  return /^[A-Za-z0-9_-]{8,512}$/.test(value) ? value : "";
}

export function requestedScopes(value) {
  return [...new Set((value || "").split(/\s+/).filter(Boolean))];
}

export function safeAuthorizationRedirect(value, expectedOrigin = window.location.origin) {
  const url = new URL(value);
  if (url.origin !== expectedOrigin || url.pathname !== "/api/v1/session/callback") {
    throw new Error("Redirection OAuth non sécurisée.");
  }
  return url.toString();
}
