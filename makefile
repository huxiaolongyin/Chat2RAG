.PHONY: api
api:
	python chat2rag/api/app.py		


.PHONY: ui
ui:
	streamlit run chat2rag/ui/app.py

.PHONY: build
build:
	docker build -t jacob0827/chat2rag:latest .


.PHONY: docker
docker:
	docker compose -f docker/docker-compose.yml --env-file .env up -d

.PHONY: save
save:
	docker save -o deploy/chat2rag0.2.2.tar jacob0827/chat2rag:latest