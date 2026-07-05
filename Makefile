PYTHON ?= python

.PHONY: setup demo genai-demo genai-image-demo genai-export-demo retention-cleanup test train evaluate api dashboard run-dashboard airflow compat-check

setup:
	./setup.sh

demo:
	./run-demo.sh

genai-demo:
	$(PYTHON) -m genai.demo

genai-image-demo:
	$(PYTHON) -m genai.image_demo --campaign-id $$(ls -1t data/generated/manifests/*.json | head -n 1 | xargs basename | sed 's/\.json$$//')

genai-export-demo:
	$(PYTHON) -m genai.export_demo --campaign-id $$(ls -1t data/generated/manifests/*.json | head -n 1 | xargs basename | sed 's/\.json$$//')

retention-cleanup:
	$(PYTHON) -m genai.retention_cleanup

test:
	$(PYTHON) -m pytest tests/

compat-check:
	$(PYTHON) -m utils.runtime_baseline
	$(PYTHON) -m pytest tests/test_runtime_baseline.py

train:
	$(PYTHON) models/train_model.py

evaluate:
	$(PYTHON) models/evaluate_model.py

api:
	uvicorn scoring.fastapi_app:app --reload

dashboard:
	streamlit run streamlit_app.py

run-dashboard:
	streamlit run streamlit_app.py

airflow:
	cd airflow && docker compose up --build
