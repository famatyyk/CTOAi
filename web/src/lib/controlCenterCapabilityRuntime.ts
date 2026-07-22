import {
  CONTROL_CENTER_CAPABILITY_IDS,
  collectControlCenterEvidenceSlices,
  type ControlCenterCapabilityId,
  type ControlCenterEvidenceSliceMap,
} from "@/lib/controlCenterEvidence"
import {
  projectControlCenterCapabilityFromSlice,
  projectControlCenterOpsSummary,
  type ControlCenterCapabilityDetail,
  type ControlCenterCapabilitySummary,
} from "@/lib/controlCenterCapabilities"

type SliceCollector = (
  ids: readonly ControlCenterCapabilityId[],
) => Promise<Partial<ControlCenterEvidenceSliceMap>>

/** Collect the compact, read-only capability index without the legacy full payload. */
export async function collectControlCenterCapabilitySummary(): Promise<ControlCenterCapabilitySummary> {
  const collector: SliceCollector = collectControlCenterEvidenceSlices
  const slices = await collector(CONTROL_CENTER_CAPABILITY_IDS)
  assertCompleteSlices(slices, CONTROL_CENTER_CAPABILITY_IDS)
  return projectControlCenterOpsSummaryFromSlices(slices)
}

/** Collect exactly one evidence capability.  A missing slice is an error, never a fallback to wider data. */
export async function collectControlCenterCapabilityDetail(
  capabilityId: ControlCenterCapabilityId,
): Promise<ControlCenterCapabilityDetail> {
  const collector: SliceCollector = collectControlCenterEvidenceSlices
  const slices = await collector([capabilityId])
  assertCompleteSlices(slices, [capabilityId])
  return projectControlCenterCapabilityFromSlice(slices[capabilityId])
}

export function assertCompleteSlices(
  slices: Partial<ControlCenterEvidenceSliceMap>,
  ids: readonly ControlCenterCapabilityId[],
): asserts slices is ControlCenterEvidenceSliceMap {
  const missing = ids.filter((id) => !slices[id])
  if (missing.length) {
    throw new Error(`Control Center evidence is incomplete for ${missing.join(", ")}.`)
  }
}

export function projectControlCenterOpsSummaryFromSlices(
  slices: Partial<ControlCenterEvidenceSliceMap>,
): ControlCenterCapabilitySummary {
  return projectControlCenterOpsSummary(slices)
}
