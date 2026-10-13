# Workstream report format

Used by the four DD reviewers (financial-dd, legal-dd, commercial-dd, team-dd).
Replace <PFX> with your workstream prefix: FIN, LEG, COM or TEAM.

## Citations
Every finding cites where it came from, precisely enough that someone can open the file and find it:
- text extract of a spreadsheet: [D021 P&L!F28]   (sheet name, column letter, row number from the "R28:" line)
- PDF or slide: [D033 p.12]  or  [D003 slide 1]
- Word document: [D004 §Liquidation preference]  (nearest heading or clause name)
Several sources: [D021 P&L!F28; D034 p.7].

## Confidence labels
- VERIFIED: supported by a primary document (accounts, signed agreement, registry extract, servicer report)
- MGMT CLAIM: stated by management (deck, infomemo, model assumptions) and not independently supported
- DERIVED: you calculated it from cited figures; show the formula
- CONFLICT: two documents disagree; give both values and both sources

## File structure (write exactly these headings)

WORKSTREAM: <name>
DOCUMENTS REVIEWED: <IDs, with "partial: pages x–y" where you did not read everything>
DOCUMENTS ASSIGNED BUT NOT READ: <IDs and why, or "none">

## FINDINGS
<PFX>-01. <one factual statement with the number> | <VERIFIED / MGMT CLAIM / DERIVED / CONFLICT> | [<citation>]
<PFX>-02. ...
(15 to 40 findings. One fact per line. No adjectives, no conclusions: just facts.)

## RED FLAGS
- <KILL / MAJOR / MINOR>: <what>, <why it matters for the investment> (<PFX>-xx)
(KILL = would stop the deal on its own if confirmed. Use it rarely and only with evidence.)

## INCONSISTENCIES
- <metric>: <value A> [<source A>] vs <value B> [<source B>]

## MISSING
- <document or data needed> | <P1/P2/P3> | <why it matters>

## QUESTIONS FOR MANAGEMENT
- <specific question, answerable by the company>
