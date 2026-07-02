export type ChatQualityLevel = "approved" | "review" | "draft"

export type ChatQualityAssessment = {
  level: ChatQualityLevel
  score: number
  issues: string[]
}

export type ChatPublicationDecision = {
  blocked: boolean
  label: string
  detail: string
  missingTemplateSections?: string[]
}

export type ChatReviewTemplate = {
  requiredSections: string[]
  missingSections: string[]
  satisfied: boolean
}

function looksLikeCode(content: string): boolean {
  return (
    /```/.test(content) ||
    /^\s{4,}\S/m.test(content) ||
    /^\s*(class|def|function|import|from|return|if|for|while|try|catch|except|const|let|var|local|export)\b/m.test(content) ||
    /^\s*\w[\w\s]*\s*[:=]\s*.+$/m.test(content)
  )
}

function countCodeLines(content: string): number {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0).length
}

export function evaluateControlCenterChatTemplate(content: string): ChatReviewTemplate {
  const codeLike = looksLikeCode(content)
  const requiredSections = ["test", "edge cases", "failure mode", "usage"]
  if (!codeLike) {
    return { requiredSections, missingSections: [], satisfied: true }
  }

  const lowered = content.toLowerCase()
  const hasSection = (pattern: RegExp) => pattern.test(lowered)
  const sectionPatterns: Record<string, RegExp> = {
    test: /(^|\n)\s*(#{1,3}\s*)?(test|tests)\s*[:\-]/i,
    "edge cases": /(^|\n)\s*(#{1,3}\s*)?edge\s+cases?\s*[:\-]/i,
    "failure mode": /(^|\n)\s*(#{1,3}\s*)?(failure\s+mode|failure\s+modes|error\s+path|error\s+paths)\s*[:\-]/i,
    usage: /(^|\n)\s*(#{1,3}\s*)?(usage|how to use|how-to-use)\s*[:\-]/i,
  }
  const missingSections = requiredSections.filter((section) => {
    const pattern = sectionPatterns[section]
    return !hasSection(pattern)
  })

  return {
    requiredSections,
    missingSections,
    satisfied: missingSections.length === 0,
  }
}

export function assessControlCenterChatQuality(content: string): ChatQualityAssessment {
  const text = content.trim()
  if (!text) {
    return { level: "draft", score: 0, issues: ["Empty assistant output."] }
  }

  const issues: string[] = []
  let score = 100
  const codeLike = looksLikeCode(text)
  const lines = countCodeLines(text)
  const lowered = text.toLowerCase()

  if (!codeLike) {
    return { level: "approved", score, issues }
  }

  if (lines > 8 && !/\b(test|pytest|unittest|describe|it\()\b/i.test(text)) {
    score -= 20
    issues.push("Brak testów lub przykładu walidacji.")
  }

  if (!/\b(try|except|catch|raise|assert|if\s+not|validate|validation|bounds|range|guard)\b/i.test(text)) {
    score -= 20
    issues.push("Brak jawnej walidacji wejścia albo obsługi błędów.")
  }

  if (/\bself\.\w+\s*\(/i.test(text) || /\b(reveal|render|process|handle|walk|dfs|recurs|recurse)\b/i.test(text)) {
    score -= 15
    issues.push("Możliwa ryzykowna rekurencja bez bezpiecznego ograniczenia.")
  }

  if (/\b(input\(|print\(|stdin|console\.log\()/i.test(text) && !/\b(cli|argparse|usage|help)\b/i.test(text)) {
    score -= 10
    issues.push("Kod jest CLI-only bez jasnego API albo warstwy integracji.")
  }

  if (/todo|fixme|xxx|hack/i.test(text)) {
    score -= 20
    issues.push("Kod zawiera placeholdery albo techniczne prowizorki.")
  }

  if (/\b(random\b|randint\b)/i.test(text) && !/\b(seed|deterministic|tests?)\b/i.test(text)) {
    score -= 10
    issues.push("Logika losowa bez deterministycznego trybu testowego.")
  }

  if (!/\b(win|victory|complete|success|done)\b/i.test(lowered) && lines > 12) {
    score -= 10
    issues.push("Brakuje wyraźnego warunku sukcesu lub końca procesu.")
  }

  if (score < 0) score = 0
  const level: ChatQualityLevel = score >= 85 ? "approved" : score >= 70 ? "review" : "draft"
  return { level, score, issues }
}

export function decideControlCenterChatPublication(
  assessment: ChatQualityAssessment,
  strictReviewMode: boolean,
  template?: ChatReviewTemplate,
): ChatPublicationDecision {
  if (!strictReviewMode) {
    return {
      blocked: false,
      label: "published",
      detail: "",
    }
  }

  if (assessment.level === "draft") {
    return {
      blocked: true,
      label: "blocked",
      detail: "Code review mode blocked publication because the answer still looks like a draft.",
    }
  }

  if (template && !template.satisfied) {
    return {
      blocked: true,
      label: "blocked",
      detail: "Hard review blocked publication because the answer is missing the minimal code review template.",
      missingTemplateSections: template.missingSections,
    }
  }

  return {
    blocked: false,
    label: assessment.level === "review" ? "needs-review" : "published",
    detail: assessment.level === "review" ? "Published with review warning." : "",
  }
}
