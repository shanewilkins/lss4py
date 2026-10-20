# Review the Current LSS4PY Working Tree

Review the current LSS4PY working-tree changes using notes/change_review_prompt.md.

Compare tracked changes against HEAD and include relevant untracked files. Review
staged and unstaged changes together. Read affected callers, tests, public
contracts, and governing ADRs.

Focus on concrete defects and regressions: analytical correctness, denominator
semantics, backend parity, validation and normalization, serialization, bundle
restoration and migration, source verification, and installed-package behavior.

Run the smallest credible checks for affected behavior. Record what passed,
failed, or could not be verified. Do not modify the implementation or regenerate
reference evidence.

Lead with actionable findings ordered P0–P3. Each finding must identify the
affected file and tight line range, triggering conditions, actual versus intended
behavior, user consequence, and supporting evidence. Separate pre-existing issues
and unresolved questions from defects introduced by these changes.

Do not invent findings or perform a whole-project release audit. If no actionable
defects are established, say so and describe material validation limits.

Finish with a concise validation summary and whether the change can proceed,
needs fixes, or lacks sufficient evidence.
