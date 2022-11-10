.PHONY: analyze hello

vendor:
	pip install -r requirements.txt

analyze:
	PYTHONPATH=. streamlit run ./bin/analyze.py

hello:
	python hello/hello.py
