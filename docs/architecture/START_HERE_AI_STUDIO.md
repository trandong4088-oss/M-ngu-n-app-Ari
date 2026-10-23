# ARO Studio — START HERE (Fresh Project)

## Authority and purpose
This is a fresh ARO Studio implementation. The numbered files `00`–`13` are the design/engineering baseline. They describe the target architecture and intended behavior; they do **not** prove that any implementation, build, test, or Golden run already exists or has passed.

## Non-negotiable owner instructions
1. Work incrementally. Do not generate the whole application in one response or one operation.
2. For the first task, do **A01 only** from `10_ARENA_BUILD_BOOK.md`: establish the empty repository foundation and a reproducible runtime. Do not start A02 or later until the owner reviews the A01 deliverables and explicitly approves the next task.
3. Do not build the complete Android UI, all modules, or the full worker pipeline in the first task. Do not skip ahead to A19–A24; any historical note suggesting early Android work is superseded by the fresh-project owner instruction here.
4. Do not use an old APK, old repository, old handoff, or prior implementation state as source code or as evidence that features exist. Create a clean project from the source tree in `02_FINAL_SOURCE_TREE.md` only as each task requires.
5. Do not use mock implementations, placeholder functions, fake progress, fake IDs, fake artifacts, or hard-coded success states to satisfy a required production interface. A capability must be marked unimplemented until its real behavior and tests exist.
6. Do not say a command/test/build passed unless it was actually executed in this environment. Distinguish `PASS`, `FAIL`, `BLOCKED`, and `NOT_RUN`, and include the exact command plus observed result.
7. Do not delete or replace approved files without explaining why and identifying the affected contracts. Preserve existing work between approved tasks.
8. Never put API keys, OAuth tokens, passwords, private user data, private media, or credentials in source code, logs, test fixtures, README, or Git history. Use placeholders in examples and a real secret store/runtime auth flow when implemented.
9. No automatic paid provider or cloud fallback unless the job configuration explicitly permits it. Never claim OCR, translation, TTS, rendering, or Drive publication is complete without producing and validating the real output.
10. When requirements are ambiguous or dependencies are unavailable, document the blocker and stop at that boundary. Do not invent an alternative implementation silently.

## First response/task: A01 only
Before editing files, briefly report the intended A01 scope and list the exact files to create. Then implement only A01.

A01 acceptance must be based on the taskbook's own `GOAL`, `INPUT CONTRACT`, `FILES TO CREATE`, `EXACT IMPLEMENTATION`, `TESTS`, `EXPECTED RESULT`, `FAILURE CONDITIONS`, and `OUTPUT ARTIFACT` sections. At minimum, provide:
- changed/created file list;
- commands actually executed;
- test/build outputs, including failures;
- runtime/dependency facts actually verified versus still unknown;
- a concise A01 acceptance report with PASS/FAIL/BLOCKED/NOT_RUN per criterion;
- proposed next task, without starting it.

Do not mark A01 complete merely because files exist. If a prerequisite cannot be installed or a test cannot run, say so explicitly and leave the relevant criterion BLOCKED or NOT_RUN.

## Required document reading order
Read `01_PRODUCT_BLUEPRINT.md` → `03_DRIVE_JOB_PROTOCOL.md` → `04_CORE_DATA_MODELS.md` → `02_FINAL_SOURCE_TREE.md` → the A01 section in `10_ARENA_BUILD_BOOK.md`. Read the relevant domain spec and `11_GOLDEN_ACCEPTANCE.md` when the corresponding task begins. `13_UNKNOWN_AND_DECISIONS.md` records design decisions and unresolved risks; do not present an unknown as verified.

## Status vocabulary
- `PASS`: exact acceptance criterion has been executed and supported by evidence.
- `FAIL`: criterion was tested and failed.
- `BLOCKED`: a required prerequisite is unavailable or a dependency prevents execution.
- `NOT_RUN`: no relevant test or check was executed.
- `IMPLEMENTED_UNVERIFIED`: code exists, but required runtime acceptance has not been demonstrated.

## Handoff rule
Return a reviewable diff or a complete set of created files, plus tests and evidence. Wait for explicit owner approval before moving to another task. Never create the whole app just to make the screens look complete.
