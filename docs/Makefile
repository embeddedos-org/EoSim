# EoSim Documentation Build
#
# Prerequisites:
#   sudo apt install pandoc texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended
#   pip install doxypypy
#
# Usage:
#   make pdf        — Generate PDF book via Pandoc + LaTeX
#   make html       — Generate HTML book via Pandoc
#   make doxygen    — Generate Doxygen HTML + LaTeX
#   make all        — Build everything
#   make clean      — Remove build outputs

BOOK_SRC = book/book.md
BOOK_PDF = output/EoSim_Reference_Guide_v2.0.pdf
BOOK_HTML = output/EoSim_Reference_Guide_v2.0.html

.PHONY: all pdf html doxygen clean

all: pdf html doxygen

# ── PDF via Pandoc + LaTeX ────────────────────────────────────────────
pdf:
	@mkdir -p output
	pandoc $(BOOK_SRC) \
		-o $(BOOK_PDF) \
		--pdf-engine=xelatex \
		--toc \
		--toc-depth=3 \
		--number-sections \
		-V geometry:margin=1in \
		-V fontsize=11pt \
		-V documentclass=report \
		-V title="EoSim — World-Class Embedded Simulation Platform" \
		-V author="Srikanth Patchava & EmbeddedOS Contributors" \
		-V date="April 2026" \
		--highlight-style=tango \
		--metadata=lang:en
	@echo "PDF generated: $(BOOK_PDF)"

# ── HTML via Pandoc ───────────────────────────────────────────────────
html:
	@mkdir -p output
	pandoc $(BOOK_SRC) \
		-o $(BOOK_HTML) \
		--standalone \
		--toc \
		--toc-depth=3 \
		--number-sections \
		--highlight-style=tango \
		--metadata=title:"EoSim Reference Guide v2.0"
	@echo "HTML generated: $(BOOK_HTML)"

# ── Doxygen (API docs) ───────────────────────────────────────────────
doxygen:
	doxygen Doxyfile
	@echo "Doxygen output: output/html/index.html"
	@echo "To build PDF from LaTeX: cd output/latex && make"

# ── Clean ─────────────────────────────────────────────────────────────
clean:
	rm -rf output/
