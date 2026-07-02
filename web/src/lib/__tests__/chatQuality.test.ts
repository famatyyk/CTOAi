import { describe, expect, it } from "vitest"
import {
  assessControlCenterChatQuality,
  decideControlCenterChatPublication,
  evaluateControlCenterChatTemplate,
} from "../chatQuality"

describe("assessControlCenterChatQuality", () => {
  it("approves plain prose", () => {
    const result = assessControlCenterChatQuality("To jest zwykła odpowiedź opisowa bez kodu.")

    expect(result.level).toBe("approved")
    expect(result.score).toBe(100)
    expect(result.issues).toHaveLength(0)
  })

  it("flags weak generated code as draft", () => {
    const result = assessControlCenterChatQuality(`
import random

class Saper:
    def reveal(self, x, y):
        if self.board[y][x] == 0:
            self.reveal(x + 1, y)
`)

    expect(result.level).toBe("draft")
    expect(result.score).toBeLessThan(60)
    expect(result.issues.join(" ")).toMatch(/walidacji|rekurencj|testów/i)
  })

  it("blocks draft code in strict review mode", () => {
    const quality = assessControlCenterChatQuality(`
class Sample:
    def go(self):
        self.go()
`)
    const decision = decideControlCenterChatPublication(quality, true)

    expect(quality.level).toBe("draft")
    expect(decision.blocked).toBe(true)
    expect(decision.label).toBe("blocked")
  })

  it("requires the hard review template for code answers", () => {
    const template = evaluateControlCenterChatTemplate(`
def add(a, b):
    return a + b

Test:
Usage:
`)

    expect(template.satisfied).toBe(false)
    expect(template.missingSections).toEqual(expect.arrayContaining(["edge cases", "failure mode"]))
  })

  it("accepts a code answer with the full hard review template", () => {
    const template = evaluateControlCenterChatTemplate(`
def add(a, b):
    return a + b

## Test:
pytest test_math.py

## Edge cases:
- non-numeric input
- overflow handling

## Failure mode:
- raise TypeError on bad input

## Usage:
- add(1, 2)
`)

    const decision = decideControlCenterChatPublication(
      { level: "approved", score: 92, issues: [] },
      true,
      template,
    )

    expect(template.satisfied).toBe(true)
    expect(decision.blocked).toBe(false)
    expect(decision.label).toBe("published")
  })
})
