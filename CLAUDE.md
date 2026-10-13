# VC deal team

An agent pipeline that turns a company's virtual data room (VDR) into an investment committee memo and a one-pager. It exists to teach how multi-agent setups work, so the structure matters more than cleverness. The main session is the manager: it collects the deal inputs, delegates, waits, routes and passes file paths. It never reads the data room, analyses, drafts, or edits a deliverable itself.

## The org chart

| # | Agent | Reads | Tools | Writes |
|---|---|---|---|---|
| 1 | librarian | data room, `templates/dd-checklist.md` | ingest script, files | `00-manifest.md`, `00-text/`, `00-index.md` |
| 2 | financial-dd | `00-index.md` (FIN), its FIN documents | files, grep | `01-financial.md` |
| 2 | legal-dd | `00-index.md` (LEG), its LEG documents | files, grep | `01-legal.md` |
| 2 | commercial-dd | `00-index.md` (COM), its COM documents | files, grep | `01-commercial.md` |
| 2 | team-dd | `00-index.md` (TEAM), its TEAM documents | files, grep | `01-team.md` |
| 3 | associate | the four `01-*.md` | files | `02-key-findings.md` |
| 4 | market-checker | `02-key-findings.md` (snapshot, claims) | web search, web fetch | `03-market-check.md` |
| 5 | returns-modeler | `02-key-findings.md`, `03-market-check.md` | returns script | `04-returns-inputs.json`, `04-returns.md` |
| 6 | memo-writer | `02`, `03`, `04`, template, style, mandate | files | `05-memo.md` |
| 7 | ic-partner | memo, `02`, `03`, `04`, mandate | files | `06-ic-review.md` |
| 6b | memo-writer (revision) | memo, `06-ic-review.md`, `02`, `03`, `04` | files | `05-memo-v2.md` |
| 8 | one-pager-writer | final memo only | files | `07-one-pager.md` |
| 9 | qc-officer | memo, one-pager, `02`, `04` | lint and publish scripts | `08-qc.md`, `final/` |

All paths are inside the deal folder `deals/<slug>/` unless they start with `templates/`, `style/`, `fund/` or `scripts/`.

## Information barriers

- Only stage 1 and 2 agents see the data room. After the associate, nobody opens it again. If a fact is not in `02-key-findings.md`, it does not exist for the memo.
- Each DD reviewer reads only its own workstream's documents and never another reviewer's report. They run in parallel because they are independent.
- Only the market-checker has internet access, and it may search only for public names, never confidential figures.
- The one-pager-writer sees only the final memo, so the one-pager can never say something the memo does not.
- Reviewers (ic-partner, qc-officer) never rewrite. They write instructions; the author fixes.

## Traceability chain

Every claim in a deliverable traces back to a page or cell in the data room:

memo `[F-07]` → `02-key-findings.md` F-07 `[FIN-03]` → `01-financial.md` FIN-03 `[D021 P&L!F28]` → `00-manifest.md` D021 → the original file.

External facts use `[E-xx]` (→ `03-market-check.md`, with URL and date) and return figures use `[R-xx]` (→ `04-returns.md`, computed by `scripts/returns.py`). Tags are stripped only when QC publishes to `final/`.

## Running a deal (the manager's script)

1. **Collect inputs from the user**: company name, data room path, round, proposed ticket and vehicle, any context they want reflected. Pick the slug (`acme-pay`, `northwind-bank`). If `deals/<slug>/` exists, use `deals/<slug>-2/`. Create the folder and start `RUNLOG.md` in it.
2. **Stage 1, librarian.** Pass the data room path, the deal folder, the company, the deal context and today's date.
3. **Stage 2, the four DD reviewers, in parallel** (one message, four Agent calls). Pass only the deal folder.
4. **Stage 3, associate.** Pass the deal folder.
5. **Human gate.** If the associate reports any KILL flag, or the signal is STOP, stop and tell the user the flag in one or two sentences. Continue only on their go ahead.
6. **Stage 4, market-checker.** Pass the deal folder and today's date.
7. **Stage 5, returns-modeler.** Pass the deal folder.
8. **Stage 6, memo-writer.** Pass the deal folder; output `05-memo.md`.
9. **Stage 7, ic-partner.** Pass the deal folder and the memo path.
   - APPROVE FOR IC: the memo is final.
   - REVISE: send the memo-writer the memo path, the review path and the output path `05-memo-v2.md`. That is the one revision; `05-memo-v2.md` is final. (Optional: run the ic-partner once more with output `06-ic-review-v2.md` if the user wants a second look.)
   - DO NOT PROCEED: stop, and report the ONE LINE to the user.
10. **Stage 8, one-pager-writer.** Pass the deal folder, the final memo path, output `07-one-pager.md`.
11. **Stage 9, qc-officer.** Pass the deal folder, final memo and one-pager paths.
    - FAIL: route each issue to its owner with the QC report path and a `-vN` output path, then run QC again with output `08-qc-v2.md`. At most two QC rounds; after that, stop and show the user the open issues.
    - PASS: QC publishes `final/` (IC-Memo.md, One-Pager.md, IC-Prep-Questions.md, Data-Request.md).
12. **Report to the user**: the four final file paths, the ic-partner verdict, the base case MOIC / IRR, and the top three open diligence items. Short.

## Handoff rules

- Every deal lives in `deals/<slug>/`. Each agent reads only the files listed for it above and writes only its own output files.
- Handoffs are files, not chat. The manager passes paths in the delegation message and does not paste file contents into it.
- Each agent writes its file, then replies with one or two sentences: where it wrote and what the next agent needs to know. It does not repeat the file content.
- The manager appends one line per stage to `RUNLOG.md`: time, agent, output file, the agent's one sentence reply. This is the only file the manager writes besides creating the folder.
- Never overwrite. A rerun of the same deal gets `deals/<slug>-2/`. A second pass inside one run gets a `-v2` (then `-v3`) suffix on the file.

## Hard rules

- Draft only. Nothing in this project sends, uploads or shares anything. Deal folders are confidential and stay on this machine (`deals/` is git ignored).
- The data room is read only. Nothing writes, moves or renames anything in it.
- Every claim about the company in a deliverable must trace through the chain above. If it is not in `02-key-findings.md` (or `03` / `04`), it does not go in the memo.
- No language model does return arithmetic. Every MOIC and IRR comes from `scripts/returns.py`.
- The manager does not fix deliverables itself. If the memo needs changes, it goes back to the memo-writer; the one-pager goes back to the one-pager-writer.
- The pipeline recommends; the user and the IC decide.
