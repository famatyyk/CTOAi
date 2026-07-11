export const CTOA_TOKEN_COOKIE_NAME = "ctoa_token"
export const CTOA_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24

export function ctoaTokenCookieOptions(maxAge = CTOA_TOKEN_MAX_AGE_SECONDS) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  }
}
