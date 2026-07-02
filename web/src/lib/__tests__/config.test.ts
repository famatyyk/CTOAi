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
})
