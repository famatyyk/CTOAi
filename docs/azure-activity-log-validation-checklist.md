# Azure Activity Log Validation Checklist (PR)

- [ ] Response starts with timeline summary.
- [ ] Response includes operationName.
- [ ] Response includes status and subStatus.
- [ ] Response includes affected esourceId.
- [ ] Response includes caller.
- [ ] Response includes correlationId.
- [ ] Security-sensitive/high-impact changes are explicitly highlighted.
- [ ] Facts and inference are explicitly separated.
- [ ] A concrete next investigation step is provided.
- [ ] If input is partial screenshot/excerpt, response asks for raw JSON/text log.