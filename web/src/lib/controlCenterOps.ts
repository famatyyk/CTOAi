import { execFile } from "node:child_process"
import { promisify } from "node:util"

const execFileAsync = promisify(execFile)

const DEFAULT_VPS_HOST = "116.202.96.250"
const DEFAULT_VPS_PORT = "2222"
const DEFAULT_VPS_USER = "ctoa-admin"
const DEFAULT_VPS_DOCKER_USER = "root"
const DEFAULT_VPS_KEY =
  process.platform === "win32"
    ? "C:\\Users\\zycie\\.ssh\\ctoa_vps_auto_ed25519"
    : "/mnt/c/users/zycie/.ssh/ctoa_vps_auto_ed25519"

const SSH_BIN = process.env.CTOA_SSH_BIN || "ssh"
const GH_BIN =
  process.env.CTOA_GH_BIN ||
  (process.platform === "win32" ? "C:\\Program Files\\GitHub CLI\\gh.exe" : "gh")
const REPO = process.env.CTOA_GITHUB_REPO || "famatyyk/CTOAi"

export type OpsTile = {
  id: "vps" | "docker" | "bot" | "github"
  label: string
  status: "online" | "warning" | "offline" | "unknown"
  headline: string
  detail: string
  source: string
  updatedAt: string
  raw?: string
}

export type VpsDiskDetail = {
  filesystem: string
  sizeBytes: number
  usedBytes: number
  availableBytes: number
  usePercent: number
  mount: string
}

export type DockerImageDetail = {
  repository: string
  tag: string
  imageId: string
  createdSince: string
  size: string
}

export type BotLogPreview = {
  container: string
  lines: string[]
}

export type GithubRunDetail = {
  databaseId: number
  name: string
  displayTitle: string
  status: string
  conclusion: string
  event: string
  headBranch: string
  createdAt: string
  url: string
}

export type ControlCenterOps = {
  generatedAt: string
  tiles: OpsTile[]
  details: {
    vpsDisk: VpsDiskDetail | null
    dockerImages: DockerImageDetail[]
    botLogs: BotLogPreview | null
    githubRuns: GithubRunDetail[]
  }
}

async function runFixedCommand(file: string, args: string[], timeout = 8000): Promise<string> {
  const result = await execFileAsync(file, args, {
    timeout,
    windowsHide: true,
    maxBuffer: 1024 * 1024,
  })
  return [result.stdout, result.stderr].filter(Boolean).join("\n").trim()
}

async function runVps(command: string, timeout = 9000, userOverride?: string): Promise<string> {
  const host = process.env.CTOA_VPS_HOST || DEFAULT_VPS_HOST
  const port = process.env.CTOA_VPS_PORT || DEFAULT_VPS_PORT
  const user = userOverride || process.env.CTOA_VPS_USER || DEFAULT_VPS_USER
  const key = process.env.CTOA_VPS_KEY || DEFAULT_VPS_KEY

  return runFixedCommand(
    SSH_BIN,
    [
      "-i",
      key,
      "-p",
      port,
      "-o",
      "BatchMode=yes",
      "-o",
      "ConnectTimeout=5",
      "-o",
      "StrictHostKeyChecking=accept-new",
      `${user}@${host}`,
      command,
    ],
    timeout,
  )
}

function nowIso(): string {
  return new Date().toISOString()
}

function unavailableTile(id: OpsTile["id"], label: string, source: string, error: unknown): OpsTile {
  return {
    id,
    label,
    status: "unknown",
    headline: "Not available",
    detail: error instanceof Error ? error.message : "Read-only probe failed.",
    source,
    updatedAt: nowIso(),
  }
}

function parseDiskUsage(output: string): OpsTile {
  const lines = output.split(/\r?\n/).filter(Boolean)
  const data = lines[1] || ""
  const parts = data.trim().split(/\s+/)
  const usedPercent = parts[4] || "unknown"
  const available = parts[3] || "unknown"
  const status = usedPercent.endsWith("%") && Number.parseInt(usedPercent, 10) >= 90 ? "warning" : "online"

  return {
    id: "vps",
    label: "VPS disk",
    status,
    headline: `${available} free`,
    detail: `Root filesystem usage: ${usedPercent}`,
    source: "ssh df -h /",
    updatedAt: nowIso(),
    raw: output,
  }
}

function parseDiskDetail(output: string): VpsDiskDetail {
  const lines = output.split(/\r?\n/).filter(Boolean)
  const data = lines[1] || ""
  const parts = data.trim().split(/\s+/)
  const usePercent = Number.parseInt((parts[4] || "0").replace("%", ""), 10)

  return {
    filesystem: parts[0] || "unknown",
    sizeBytes: Number.parseInt(parts[1] || "0", 10),
    usedBytes: Number.parseInt(parts[2] || "0", 10),
    availableBytes: Number.parseInt(parts[3] || "0", 10),
    usePercent: Number.isFinite(usePercent) ? usePercent : 0,
    mount: parts[5] || "/",
  }
}

function parseDocker(output: string): OpsTile {
  const lower = output.toLowerCase()
  const reclaimable = output.match(/reclaimable\s+([^\n]+)/i)?.[1]?.trim()
  const status = lower.includes("error") || lower.includes("cannot connect") ? "warning" : "online"

  return {
    id: "docker",
    label: "Docker store",
    status,
    headline: reclaimable ? `Reclaimable ${reclaimable}` : "System df available",
    detail: "Read-only Docker image/container/storage report from VPS.",
    source: "ssh docker system df",
    updatedAt: nowIso(),
    raw: output,
  }
}

function parseBot(output: string): OpsTile {
  const lines = output.split(/\r?\n/).filter(Boolean)
  const botLine = lines.find((line) => line.toLowerCase().includes("infra-bot"))
  const isUp = Boolean(botLine?.toLowerCase().includes("up"))
  const isRestarting = Boolean(botLine?.toLowerCase().includes("restart"))

  return {
    id: "bot",
    label: "Bot runtime",
    status: isUp && !isRestarting ? "online" : isRestarting ? "warning" : "unknown",
    headline: botLine ? (isUp ? "infra-bot is up" : "infra-bot visible") : "infra-bot not listed",
    detail: botLine || "Container list did not include infra-bot.",
    source: "ssh docker ps",
    updatedAt: nowIso(),
    raw: output,
  }
}

function parseGithub(output: string): OpsTile {
  const runs = JSON.parse(output) as Array<{ status?: string; conclusion?: string; name?: string }>
  const active = runs.filter((run) => run.status && run.status !== "completed").length
  const failures = runs.filter((run) => run.conclusion === "failure").length
  const status = failures > 0 ? "warning" : "online"

  return {
    id: "github",
    label: "GitHub CI",
    status,
    headline: `${runs.length} recent runs`,
    detail: `${active} active, ${failures} failed in the latest sample.`,
    source: "gh run list",
    updatedAt: nowIso(),
    raw: output,
  }
}

function parseDockerImages(output: string): DockerImageDetail[] {
  return output
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line) as Record<string, string>)
    .map((image) => ({
      repository: image.Repository || "<none>",
      tag: image.Tag || "<none>",
      imageId: image.ID || "",
      createdSince: image.CreatedSince || "",
      size: image.Size || "",
    }))
}

function parseBotLogs(output: string): BotLogPreview {
  return {
    container: "infra-bot-1",
    lines: output.split(/\r?\n/).filter(Boolean).slice(-40),
  }
}

function parseGithubRuns(output: string): GithubRunDetail[] {
  return JSON.parse(output) as GithubRunDetail[]
}

export async function collectControlCenterOps(): Promise<ControlCenterOps> {
  const dockerUser = process.env.CTOA_VPS_DOCKER_USER || DEFAULT_VPS_DOCKER_USER

  const githubRunArgs = [
    "run",
    "list",
    "--repo",
    REPO,
    "--limit",
    "10",
    "--json",
    "status,conclusion,name,displayTitle,databaseId,event,headBranch,createdAt,url",
  ]

  const [vps, docker, bot, github, vpsDisk, dockerImages, botLogs, githubRuns] = await Promise.all([
    runVps("df -h /")
      .then(parseDiskUsage)
      .catch((error) => unavailableTile("vps", "VPS disk", "ssh df -h /", error)),
    runVps("docker system df", 9000, dockerUser)
      .then(parseDocker)
      .catch((error) => unavailableTile("docker", "Docker store", `ssh ${dockerUser}@vps docker system df`, error)),
    runVps("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}'", 9000, dockerUser)
      .then(parseBot)
      .catch((error) => unavailableTile("bot", "Bot runtime", `ssh ${dockerUser}@vps docker ps`, error)),
    runFixedCommand(GH_BIN, ["run", "list", "--repo", REPO, "--limit", "10", "--json", "status,conclusion,name"], 9000)
      .then(parseGithub)
      .catch((error) => unavailableTile("github", "GitHub CI", "gh run list", error)),
    runVps("df -B1 /")
      .then(parseDiskDetail)
      .catch(() => null),
    runVps("docker images --format '{{json .}}'", 9000, dockerUser)
      .then(parseDockerImages)
      .catch(() => []),
    runVps("docker logs --tail 40 infra-bot-1 2>&1", 9000, dockerUser)
      .then(parseBotLogs)
      .catch(() => null),
    runFixedCommand(GH_BIN, githubRunArgs, 9000)
      .then(parseGithubRuns)
      .catch(() => []),
  ])

  return {
    generatedAt: nowIso(),
    tiles: [vps, docker, bot, github],
    details: {
      vpsDisk,
      dockerImages,
      botLogs,
      githubRuns,
    },
  }
}
