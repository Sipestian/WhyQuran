.PHONY: test verify reports check

test:
	python3 -m unittest discover -s tests -v

verify:
	python3 -m quran_research verify

reports: verify
	python3 -m quran_research inventory
	python3 -m quran_research characters
	python3 -m quran_research characters --corpus uthmani
	python3 -m quran_research universe
	python3 -m quran_research build

check: test reports
