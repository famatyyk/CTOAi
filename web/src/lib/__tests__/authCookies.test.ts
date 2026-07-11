import { afterEach, describe, expect, it, vi } from "vitest"
import { CTOA_TOKEN_COOKIE_NAME, CTOA_TOKEN_MAX_AGE_SECONDS, ctoaTokenCookieOptions } from "../authCookies"

describe("auth cookie options", () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("keeps ctoa token cookies httpOnly and sameSite lax", () => {
    vi.stubEnv("NODE_ENV", "development")

    expect(CTOA_TOKEN_COOKIE_NAME).toBe("ctoa_token")
    expect(ctoaTokenCookieOptions()).toEqual({
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      path: "/",
      maxAge: CTOA_TOKEN_MAX_AGE_SECONDS,
    })
  })

  it("sets Secure for production ctoa token cookies", () => {
    vi.stubEnv("NODE_ENV", "production")

    expect(ctoaTokenCookieOptions()).toMatchObject({
      httpOnly: true,
      sameSite: "lax",
      secure: true,
      path: "/",
    })
  })

  it("keeps logout cookies scoped and secure in production", () => {
    vi.stubEnv("NODE_ENV", "production")

    expect(ctoaTokenCookieOptions(0)).toEqual({
      httpOnly: true,
      sameSite: "lax",
      secure: true,
      path: "/",
      maxAge: 0,
    })
  })
})
