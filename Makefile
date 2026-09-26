.PHONY: followup-paired leaderboard paper

followup-paired:
	PYTHONPATH=. python scripts/sec_followup_paired_analysis.py

leaderboard:
	PYTHONPATH=. python scripts/sec_build_final_leaderboard_artifact.py

paper:
	cd paper && pdflatex main_8page_v2.tex && bibtex main_8page_v2 && pdflatex main_8page_v2.tex && pdflatex main_8page_v2.tex
