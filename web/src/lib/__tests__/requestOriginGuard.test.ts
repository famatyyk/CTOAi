import { describe, expect, it } from "vitest"
import { validateSameOriginRequest } from "../requestOriginGuard"

function guardedRequest(headers: HeadersInit) {
  return new Request("http://localhost/api/example", {
    method: "POST",
    headers,
  })
}

describe("same-origin request guard", () => {
  it("accepts same-origin Origin and Referer values", () => {
    expect(validateSameOriginRequest(guardedRequest({ Origin: "http://localhost" }), { requestLabel: "example" })).toEqual({
      ok: true,
    })
    expect(
      validateSameOriginRequest(guardedRequest({ Referer: "http://localhost/control-center" }), {
        requestLabel: "example",
      }),
    ).toEqual({ ok: true })
  })

  it("rejects explicit cross-site request signals", () => {
    expect(
      validateSameOriginRequest(guardedRequest({ Origin: "https://attacker.example" }), {
        requestLabel: "example",
      }),
    ).toEqual({ ok: false, error: "Cross-site example requests are not allowed." })
    expect(
      validateSameOriginRequest(guardedRequest({ "Sec-Fetch-Site": "cross-site" }), {
        requestLabel: "example",
      }),
    ).toEqual({ ok: false, error: "Cross-site example requests are not allowed." })
    expect(
      validateSameOriginRequest(guardedRequest({ Referer: "https://attacker.example/x" }), {
        requestLabel: "example",
      }),
    ).toEqual({ ok: false, error: "Cross-site example requests are not allowed." })
  })

  it("rejects malformed origin and referer headers", () => {
    expect(validateSameOriginRequest(guardedRequest({ Origin: "not a url" }), { requestLabel: "example" })).toEqual({
      ok: false,
      error: "Invalid example request origin.",
    })
    expect(validateSameOriginRequest(guardedRequest({ Referer: "not a url" }), { requestLabel: "example" })).toEqual({
      ok: false,
      error: "Invalid example request referer.",
    })
  })
})
