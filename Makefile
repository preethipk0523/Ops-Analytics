.PHONY: all data test dashboard clean
PY ?= python

all: data
data:
	$(PY) -m src.generate_data
	$(PY) -m src.clean_data
	$(PY) -m src.load_db
	$(PY) -m src.run_kpis
test:
	$(PY) -m pytest -q
dashboard:
	streamlit run dashboard/app.py
clean:
	rm -rf data/raw data/clean data/ops.db outputs
