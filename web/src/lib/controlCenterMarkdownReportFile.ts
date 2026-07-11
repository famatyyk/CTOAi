import { lstat, open } from "node:fs/promises"

export const MAX_CONTROL_CENTER_MARKDOWN_REPORT_BYTES = 1024 * 1024

export class ControlCenterMarkdownReportTooLargeError extends Error {
  constructor(filePath: string, size: number, maxBytes = MAX_CONTROL_CENTER_MARKDOWN_REPORT_BYTES) {
    super(`Control Center markdown report is too large to display safely: ${filePath} (${size}/${maxBytes} bytes)`)
    this.name = "ControlCenterMarkdownReportTooLargeError"
  }
}

export class ControlCenterMarkdownReportUnsafePathError extends Error {
  constructor() {
    super("Control Center markdown report path is not safe to read.")
    this.name = "ControlCenterMarkdownReportUnsafePathError"
  }
}

export async function readBoundedControlCenterMarkdownReport(
  filePath: string,
  maxBytes = MAX_CONTROL_CENTER_MARKDOWN_REPORT_BYTES,
): Promise<string> {
  const pathInfo = await lstat(filePath)
  if (pathInfo.isSymbolicLink() || !pathInfo.isFile()) {
    throw new ControlCenterMarkdownReportUnsafePathError()
  }

  const file = await open(filePath, "r")
  try {
    const info = await file.stat()
    if (!info.isFile()) {
      throw new ControlCenterMarkdownReportUnsafePathError()
    }

    const buffer = Buffer.allocUnsafe(maxBytes + 1)
    const { bytesRead } = await file.read(buffer, 0, maxBytes + 1, 0)
    if (bytesRead > maxBytes) {
      throw new ControlCenterMarkdownReportTooLargeError(filePath, bytesRead, maxBytes)
    }
    return buffer.subarray(0, bytesRead).toString("utf-8")
  } finally {
    await file.close()
  }
}
