import { describe, expect, it } from "vitest"
import { controlCenterSnapshot } from "../controlCenterSnapshot"

describe("controlCenterSnapshot", () => {
  it("keeps the fallback surface neutral and live-oriented", () => {
    expect(controlCenterSnapshot.phase).toContain("Live")
    expect(controlCenterSnapshot.generatedAt).toBe("runtime")
    expect(controlCenterSnapshot.health.map((card) => card.value)).toEqual(["live", "live", "file-backed"])
    expect(controlCenterSnapshot.health.map((card) => card.label)).toEqual(["Backend probe", "Ops panels", "Evidence pack"])
  })
})
