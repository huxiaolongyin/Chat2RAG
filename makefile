.PHONY: api
api:
	python chat2rag/api/app.py		


.PHONY: ui
ui:
	streamlit run chat2rag/ui/app.py