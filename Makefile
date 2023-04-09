.PHONY: analyze hello

vendor:
	PIP_INDEX_URL=https://pypi.org/simple \
	PIP_EXTRA_INDEX_URL= \
	pip install -r requirements.txt

analyze:
	@echo run "'"PYTHONPATH=. streamlit run ./bin/analyze.py"'"

hello:
	python hello/hello.py
