.PHONY: api
api:
	python chat2rag/api/app.py		

.PHONY: ui
ui:
	streamlit run chat2rag/ui/app.py

.PHONY: build
build:
	powershell -Command "$$(Get-Content VERSION.txt -First 1) | ForEach-Object { docker build -t jacob0827/chat2rag:$$_ . }; docker build -t jacob0827/chat2rag:latest ."

.PHONY: docker
docker:
	docker compose -f docker/docker-compose.yml --env-file .env up -d

.PHONY: save
save:
	powershell -Command "$$(Get-Content VERSION.txt -First 1) | ForEach-Object { docker save -o deploy/chat2rag-$$_.tar jacob0827/chat2rag:latest }"

.PHONY: mcp-server
mcp-server:
	python chat2rag/mcp/server.py