// Local runs use the API's mock auth (AUTH_MODE=mock), so no token is sent.
// The deployed build sets VITE_AUTH_MODE=cognito and adds the signed-in coach's token here.
let token: string | null = null;

export function setToken(t: string | null): void {
  token = t;
}

export async function authHeaders(): Promise<Record<string, string>> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}
