# Form Fields and Writing Rules

Source: six weekly-report approval screenshots supplied by the user. These describe the visible business form, not an API schema. They do not establish control IDs, node requirements, minimum row counts, duration rules, or draft-saving capabilities. Inspect the live UI at execution time; use a definition read when available to supplement it.

Chinese labels below are literal form identifiers. Preserve them for matching; explanatory instructions are in English.

## Five sections

All business fields listed below have required markers in the screenshots. Row numbers and controls for copying, deleting, or adding rows are not business fields.

| Section | Fields in each row, in order | Visible options or constraints |
| --- | --- | --- |
| Basic information — 一、基本信息 | 开始时间－结束时间; 时长(天); 本周整体状态 | Overall status: 正常 / 有风险 / 阻塞 (normal / at risk / blocked) |
| This week's results — 二、本周完成事项 | 事项; 对应里程碑; 完成情况; 交付物; 交付物位置 | Completion: 已完成 / 部分完成 / 延期 (completed / partial / delayed) |
| Next week's plans — 三、下周计划 | 计划事项; 目标结果; 预计完成时间; 依赖项 | Expected completion is a date |
| Risks and issues — 四、风险与问题 | 风险/问题; 影响范围; 严重程度; 需要谁支持; 建议解决方案 | Impact: 进度 / 质量 / 成本 / 交付 / 验收 (schedule / quality / cost / delivery / acceptance); severity: 高 / 中 / 低 (high / medium / low) |
| Cross-team collaboration — 五、跨团队协同需求 | 需要协同事项; 对接团队/人员; 期望完成时间; 不完成的影响 | Desired completion is a date |

All five sections appear as repeatable tables. Inspect actual rows and controls in the page. When a definition is available, `fieldList` describes nested rows, and start, end, and duration may belong to one `dateInterval`. Neither API IDs nor an API definition read are required when the UI can be reliably inspected and edited.

## Content standards

- Describe verifiable outcomes with evidence. Name the deliverable, version, or scope, and provide its real URL, path, or record identifier. Mark missing locations as questions; do not fabricate plausible addresses.
- Use actual project milestones. Ask if the milestone is unknown rather than inventing an identifier. Partial or delayed work can remain in the results section, with delivered scope, remaining work, and impact stated clearly.
- Each next-week plan needs a result that can be judged complete or incomplete, a date, and dependencies. Avoid vague descriptions such as ongoing progress, discussion, or optimization without a concrete result.
- Risks need impact and a proposed solution. Specify who needs to help and what action is needed. Mentioning someone in a support field does not authorize contacting them.
- Collaboration requests specify what the other team should deliver, by when, and the consequence of delay. Check whether a people field is plain text or a contact control in the live definition.
- Follow the user's or team's status and severity criteria. Without criteria, offer an evidence-based suggestion as unresolved where needed; do not use normal or low severity merely to fill a required cell.

## Dates, empty sections, and length

- The screenshots specify submission before Friday's end of work, approximately one page per person, and up to two for a module lead's summary. Treat these as template conventions, not authorization to schedule anything. Keep prose concise when the form has no fixed pagination.
- Next week follows the report period, not a screenshot date or the execution date automatically. Verify whether a later planned date is intentional long-term work or a mistaken period.
- Preserve the user's calendar dates and timezone in the page's date controls. Determine duration from the actual configuration and displayed calculation, including calendar versus workdays and boundary inclusion. Do not hard-code five or seven days or assume simple subtraction.
- Silence about risks, dependencies, or collaboration does not mean none. If the user explicitly confirms none, check whether zero rows are allowed. If a row is required and a dropdown lacks a not-applicable option, do not pick low severity or schedule impact to fabricate a complete row; establish the template's accepted convention.
- Unresolved placeholders belong only in private working notes. Resolve required facts before declaring the page ready for user review; a placeholder is not a valid substitute for missing information. This skill leaves submission to the user.

## Mapping checks

Match by section, row, and field label to distinguish repeated names; use observed control IDs when available. Select live dropdown options by their labels and inspect the resulting selection, not their screenshot order. Follow active visibility, external-option, and formula rules; hidden fields are neither universally required nor universally safe to omit.
