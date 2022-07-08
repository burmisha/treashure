vendor:
	pip install -r requirements.txt

analyze:
	PYTHONPATH=. streamlit run ./bin/analyze.py
