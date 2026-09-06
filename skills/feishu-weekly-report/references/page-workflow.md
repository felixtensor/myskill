# Page Access, Draft Persistence, and Review

Use the host's available, authorized browser or desktop tools and their operating instructions. This skill does not depend on a particular tool name. Source APIs can supplement discovery; they cannot establish the current unsaved page contents.

## Select the actual editing surface

| Observed state | Action |
| --- | --- |
| An accessible unsubmitted report is open | Inspect its account, form name, reporting period, and current values; reuse it |
| No report is open on the relevant accessible surface | Navigate to `审批 → 发起申请 → 周报`, or an actual supplied/returned application link; check for an existing draft before entering new content |
| The report is open in a native-client window outside browser control | Use available authorized desktop control, or establish an accessible page route without assuming the native edits transfer |
| Target state is unknown or access is denied | Identify the inaccessible surface or login/capability gap; do not interpret it as an empty form |
| Several accounts, forms, or periods plausibly match | Resolve the ambiguity before writing |
| The report has already been submitted | Report the actual state and stop this unsubmitted-form workflow |

A link may open a native client instead of an editable browser page. Verify what actually opens. Browser/native-client draft sharing has not been established by the public documentation checked for this skill. Do not create parallel forms on different surfaces or promise automatic transfer of edits.

When control is unavailable, request only the needed access or target information through the host's normal mechanism and continue independent preparation. Do not silently enable desktop control, manipulate private session storage, or use undocumented endpoints to bypass the missing capability.

## Read, fill, and verify

1. Establish the target and read all relevant sections, including rows below the fold. Observe actual labels, options, editable/computed fields, and any existing values. Record a private working snapshot sufficient to distinguish the original content from the proposed edits.
2. Merge prepared work with current content by work item and period. Preserve unrelated rows and user edits. A different-period or conflicting draft is not an empty template; clarify its disposition before replacing it.
3. Fill using observed controls and row context, not fixed screenshot coordinates or guessed hidden IDs. Add only needed rows. Select actual dropdown options; let computed duration and formulas recalculate and check their displayed results.
4. Work in small groups of related changes, then read back their values. Inspect multiline text, Chinese options, date ranges, required fields, and validation messages. Keep unresolved questions outside the live report.
5. Leave the form open for review. Do not click Submit, use submission keyboard shortcuts, or invoke creation APIs as validation. A source definition or successful typing call alone is not evidence of correct page content.

If an action times out or the session reconnects, inspect the current page before retrying. Determine whether typing or row addition already took effect; do not duplicate rows or replay an entire stale form. If the target can no longer be established, stop writes and report partial progress.

## Review loop

On feedback, read the current page again and compare it with the last verified state and requested revision. Change only the affected fields. Preserve intervening user edits; ask a narrow question when those edits conflict with the requested change. Recheck related fields such as status, deliverables, dates, or duration when the revision affects them.

Read back the modified content and return to the same visible unsubmitted form. User review does not require closing or reopening it. If the user has submitted it during the loop, stop editing and report that state without recalling, canceling, or creating another instance.

## Draft persistence is a separate capability

The official [approval changelog, October 2024](https://www.feishu.cn/hc/zh-CN/articles/360049067392-%E9%A3%9E%E4%B9%A6%E5%AE%A1%E6%89%B9%E5%8A%9F%E8%83%BD%E6%9B%B4%E6%96%B0%E6%97%A5%E5%BF%97) describes automatic saving during application entry and restoration through `打开草稿` on a later visit. It also documents:

- Only one historical draft per application, with the latest edits taking precedence.
- No draft restoration for applications configured with control groups.
- Changes to the form design can clear earlier content.
- Desktop and mobile drafts do not synchronize.

This documents client behavior, not a public API for creating drafts. Product behavior may change; verify the actual template. The screenshot's repeated tables do not by themselves establish the special control-group exclusion.

Allow normal autosave while filling. If the live UI offers an explicit save-only action and the user requests persistence, verify its semantics and use it. Do not invent a Save button, assume a saved draft identifier exists, or treat any approval-instance status as an unsubmitted draft.

For a normal filling request, readback of the populated unsubmitted page is the completion evidence; persistence can remain unverified. For an explicit save/resume request, seek a visible save confirmation applying to the current edits or actual restored-content evidence. A generic draft banner does not prove the latest edits were saved. If no evidence is available, keep the page open and report persistence as unverified.

Do not navigate away merely to test autosave during normal filling. If a save/resume request requires a restoration check, preserve a private content snapshot first, confirm the current client's restoration route, and avoid overwriting another draft. Restore and compare the actual values, then leave the form open again. If recovery cannot be established, stop before risking the current edits.
