.PHONY: api
api:
	.venv/Scripts/python chat2rag/app.py		

.PHONY: ui
ui:
	.venv/Scripts/python -m streamlit run chat2rag/ui/app.py

.PHONY: build
build:
	powershell -Command "$$(Get-Content VERSION.txt -First 1) | ForEach-Object { docker build -t jacob0827/chat2rag:$$_ . }; docker build -t jacob0827/chat2rag:latest ."

.PHONY: docker
docker:
	docker compose -f docker/docker-compose.yml --env-file .env up -d

.PHONY: save
save: build
	@powershell -Command " \
		$$version = (Get-Content VERSION.txt -First 1).Trim(); \
		Write-Host \"Building deployment package for version: $$version\"; \
		\
		if (!(Test-Path 'deploy')) { New-Item -ItemType Directory -Path 'deploy' -Force }; \
		if (!(Test-Path \"deploy/versions/$$version\")) { New-Item -ItemType Directory -Path \"deploy/versions/$$version\" -Force }; \
		\
		Write-Host \"Saving latest image...\"; \
		docker save -o deploy/chat2rag_latest.tar jacob0827/chat2rag:latest; \
		\
		Write-Host \"Saving versioned image...\"; \
		docker save -o \"deploy/versions/$$version/chat2rag_$$version.tar\" jacob0827/chat2rag:latest; \
		\
		Write-Host \"Copying configuration files...\"; \
		Copy-Item 'deploy/.env' \"deploy/versions/$$version/.env\" -ErrorAction SilentlyContinue; \
		Copy-Item 'deploy/docker-compose.yml' \"deploy/versions/$$version/docker-compose.yml\" -ErrorAction SilentlyContinue; \
		\
		Write-Host \"Deployment package created successfully for version $$version\"; \
	"
.PHONY: mcp
mcp:
	.venv/Scripts/python chat2rag/mcp/server.py

.PHONY: web
web:
	cd web && pnpm dev