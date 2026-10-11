# Anonymous Review Release Guide

This repository is prepared for double-anonymous review through an anonymized
mirror such as Anonymous GitHub.

## Recommended Workflow

1. Keep the source GitHub repository private during review if desired.
2. Push the cleaned release branch to GitHub.
3. Open `https://anonymous.4open.science/`.
4. Paste the GitHub repository URL.
5. Add identifying terms to hide, including author names, usernames, lab names,
   institution names, and personal repository URLs.
6. Generate the anonymous mirror URL.
7. Replace the manuscript placeholder
   `https://anonymous.4open.science/r/regtrace-agent-XXXX/` with the generated
   anonymous URL.
8. Open the generated anonymous URL in a private/incognito browser and check:
   author names, personal usernames, local paths, `.env` files, issue history,
   GitHub Actions logs, and profile links are not visible.

## Files That Should Not Be Released

- `.env` or any populated credential file.
- Local temporary render directories such as `tmp/`.
- Raw downloaded CMS/FDA archives unless their upstream licenses allow
  redistribution.
- Personal GitHub URLs, author names, acknowledgements, institutional logos, or
  local filesystem paths.

## What The Anonymous Artifact Should Include

- Benchmark JSONL files and split files.
- Retrieval metadata and retrieved snippets used by the benchmark.
- Label, feedback, audit, and external-corroboration fields.
- Paper-ready result tables and raw prediction/result artifacts needed to
  reproduce the reported tables.
- Prompt states, optimizer settings, and configuration files.
- Scripts and Makefile targets for table regeneration.
- Data card, reproducibility notes, and license notes.

The anonymous mirror should be treated as read-only reviewer evidence. After the
review period, the authors can either remove the mirror or redirect it to the
canonical public repository.

