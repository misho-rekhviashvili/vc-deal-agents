# VC Deal Team: a multi-agent due diligence pipeline for Claude Code

Turn a company's virtual data room (VDR) into an investment committee memo, a one-pager, IC prep questions and a data request list, using a team of 12 [Claude Code](https://claude.com/claude-code) subagents that hand work to each other through files.

The project is built to teach how multi-agent setups work: specialised roles, information barriers between them, file-based handoffs, a review and revision loop, and a final quality gate. The structure matters more than cleverness.

## The pipeline

```
data room ─► 1 librarian ─► 2 financial-dd  ┐
                            2 legal-dd      ├─► 3 associate ─► 4 market-checker ─► 5 returns-modeler
                            2 commercial-dd │   (key findings)   (only agent with    (MOIC / IRR from
                            2 team-dd       ┘                     web access)          a script)
        ─► 6 memo-writer ─► 7 ic-partner ─► 6b memo-writer v2 ─► 8 one-pager-writer ─► 9 qc-officer ─► final/
```

| # | Agent | Job | Writes |
|---|---|---|---|
| 1 | librarian | Converts the data room to text, gives every file an ID, sorts it into workstreams, lists missing documents | `00-index.md` |
| 2 | financial-dd, legal-dd, commercial-dd, team-dd | Four parallel workstream reviews; every fact cited to a page or cell | `01-*.md` |
| 3 | associate | Merges the four reports into a numbered fact register, red flags, cross workstream contradictions, returns inputs, data request list | `02-key-findings.md` |
| 4 | market-checker | Checks management's public claims and gathers peer valuation multiples | `03-market-check.md` |
| 5 | returns-modeler | Chooses bear / base / bull / management scenarios; `scripts/returns.py` does the maths | `04-returns.md` |
| 6 | memo-writer | Writes the IC memo; revises only the sections the reviewer flags | `05-memo.md`, `05-memo-v2.md` |
| 7 | ic-partner | Sceptical IC partner: traces claims, challenges the thesis, writes IC prep Q&A; never rewrites | `06-ic-review.md` |
| 8 | one-pager-writer | Condenses the final memo into one page; sees nothing else | `07-one-pager.md` |
| 9 | qc-officer | Checks numbers, tags and style; publishes clean deliverables only on PASS | `08-qc.md`, `final/` |

## Design ideas worth stealing

- **Information barriers.** Only stages 1–2 see the data room. After the associate, if a fact is not in `02-key-findings.md`, it does not exist for the memo.
- **Traceability chain.** Every claim carries a tag: memo `[F-07]` → finding F-07 `[FIN-03]` → workstream fact `[D021 P&L!F28]` → original file. Tags are stripped only on publication.
- **No LLM arithmetic.** Every MOIC and IRR comes from a deterministic script that also handles liquidation preferences, dilution, fees and carry.
- **Critics don't rewrite.** The IC partner and QC officer write instructions; the author fixes. One bounded revision loop.
- **Human gate.** The pipeline stops after key findings if a KILL red flag appears.
- **Confidentiality by default.** `deals/` is git ignored; the web enabled agent may only search public names.

## Setup

Requirements: Claude Code, Python 3.9+ (standard library only), macOS or Linux.

```bash
git clone <this repo> && cd agents-vc-team
brew install poppler      # optional but recommended: converts PDFs to searchable text (pdftotext)
```

Edit `fund/mandate.md` to describe your fund (size, stages, tickets, markets, return targets) and, if you like, `style/house-style.md` for your writing conventions.

## Running a deal

Open Claude Code in the project folder and ask:

> Run the deal pipeline for Acme Pay. Data room: ~/Downloads/AcmePay_VDR. Series B, €5M ticket.

The main session acts as the manager (see `CLAUDE.md`): it creates `deals/acme-pay/`, runs each stage, routes revisions and reports back. The outputs land in `deals/acme-pay/final/`.

## Project layout

```
.claude/agents/   the 12 agent definitions
CLAUDE.md         the manager's rulebook: org chart, handoffs, hard rules
scripts/          ingest.py, returns.py, check_style.py, publish.py (standard library only)
templates/        IC memo, one-pager, DD checklist, workstream report format
style/            house style
fund/             fund mandate
deals/            one folder per deal run (git ignored)
```

## Disclaimer

This is an educational tool. It drafts documents; it does not make investment decisions, give investment, legal or tax advice, or send anything anywhere. Always verify outputs against the source documents.

## License

MIT
