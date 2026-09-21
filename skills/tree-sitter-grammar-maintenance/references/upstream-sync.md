# Auditing after an upstream example sync


A sync is when new real-world syntax enters the repository, so it is the moment the
audit is worth the most — and also the moment it is easiest to turn into per-file
review. Do neither more nor less than this:

1. **Keep the sync a separate commit.** The source snapshot and the `SOURCE.md`
   anchor land on their own, with no grammar change riding along. Otherwise nothing
   can tell a parser regression from a change in the input.
2. **Take a census before and after the sync.** The diff separates the two things
   that just happened: files that are new, and files that existed before and now
   parse differently. The second group is the only one that can indicate a
   regression, and there should normally be none.
3. **Run the parse gate and cluster failures by mode**, not by file. Ten files
   failing on the same construct are one finding.
4. **Read only the new failures**, plus structures already known to be risky and any
   syntax you were planning to support. Files that failed before and still fail the
   same way are not new information.
5. **Turn a confirmed parser bug into a minimal corpus case.** Do not create a
   permanent record for each upstream file that exposed it.
6. **Leave expected-diagnostic and fragment files alone** unless they block the task
   at hand. If an exception is genuinely needed, keep it a short flat list with a
   reason per line.

Never edit files under `examples/` to make something pass. They are a pinned
snapshot of someone else's repository; editing them destroys the only reason they
are evidence.

---
