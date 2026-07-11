import { afterEach, describe, expect, it } from "vitest"
import { getPublicApiUrl, getServerApiUrl } from "../config"

const originalVps = process.env.VPS_API_URL
const originalPublic = process.env.NEXT_PUBLIC_API_URL

afterEach(() => {
  process.env.VPS_API_URL = originalVps
  process.env.NEXT_PUBLIC_API_URL = originalPublic
})

describe("API config", () => {
  it("falls back to local API URL", () => {
    delete process.env.VPS_API_URL
    delete process.env.NEXT_PUBLIC_API_URL

    expect(getServerApiUrl()).toBe("http://127.0.0.1:8001")
    expect(getPublicApiUrl()).toBe("http://127.0.0.1:8001")
  })

  it("trims trailing slashes", () => {
    process.env.VPS_API_URL = "https://api.example.test///"
    process.env.NEXT_PUBLIC_API_URL = "https://public.example.test/"

    expect(getServerApiUrl()).toBe("https://api.example.test")
    expect(getPublicApiUrl()).toBe("https://public.example.test")
  })

  it("allows HTTP only for local API hosts", () => {
    process.env.VPS_API_URL = "http://localhost:8001/"
    process.env.NEXT_PUBLIC_API_URL = "http://host.docker.internal:8001/"

    expect(getServerApiUrl()).toBe("http://localhost:8001")
    expect(getPublicApiUrl()).toBe("http://host.docker.internal:8001")
  })

  it("rejects non-HTTP API URL schemes", () => {
    process.env.VPS_API_URL = "file:///tmp/ctoa.sock"

    expect(() => getServerApiUrl()).toThrow("VPS_API_URL must use http:// or https://")
  })

  it("rejects API URLs with embedded credentials without echoing the value", () => {
    process.env.VPS_API_URL = "https://user:secret-token@example.test"

    expect(() => getServerApiUrl()).toThrow("VPS_API_URL must not include credentials")
    try {
      getServerApiUrl()
    } catch (error) {
      expect(String(error)).not.toContain("secret-token")
    }
  })

  it("rejects non-local HTTP API URLs", () => {
    process.env.NEXT_PUBLIC_API_URL = "http://api.example.test"

    expect(() => getPublicApiUrl()).toThrow("NEXT_PUBLIC_API_URL must use https:// for non-local hosts")
  })

  it("rejects API base URLs with query strings or fragments", () => {
    process.env.VPS_API_URL = "https://api.example.test?token=secret-token"
    process.env.NEXT_PUBLIC_API_URL = "https://public.example.test#debug"

    expect(() => getServerApiUrl()).toThrow("VPS_API_URL must not include query strings or fragments")
    expect(() => getPublicApiUrl()).toThrow("NEXT_PUBLIC_API_URL must not include query strings or fragments")
  })

  it("rejects API base URLs with path components", () => {
    process.env.VPS_API_URL = "https://api.example.test/backend"
    process.env.NEXT_PUBLIC_API_URL = "https://public.example.test/%2e%2e/admin"

    expect(() => getServerApiUrl()).toThrow("VPS_API_URL must not include path components")
    expect(() => getPublicApiUrl()).toThrow("NEXT_PUBLIC_API_URL must not include path components")
  })

  it("rejects API base URLs with backslashes without echoing the value", () => {
    process.env.VPS_API_URL = "https://api.example.test\\secret-token"

    expect(() => getServerApiUrl()).toThrow("VPS_API_URL must not include path separators")
    try {
      getServerApiUrl()
    } catch (error) {
      expect(String(error)).not.toContain("secret-token")
    }
  })
})
