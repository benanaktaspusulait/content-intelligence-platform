.PHONY: help install test check history clean

help:
	@echo "Pompom Meta Publisher - Available Commands"
	@echo "=========================================="
	@echo ""
	@echo "  make install      Install package in development mode"
	@echo "  make install-s3   Install package with S3 support"
	@echo "  make test         Test configuration"
	@echo "  make check        Quick configuration check"
	@echo "  make history      Show publication history"
	@echo "  make clean        Clean up generated files"
	@echo ""

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e .
	@echo ""
	@echo "✅ Installation complete!"
	@echo "   Activate with: source .venv/bin/activate"
	@echo ""

install-s3:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[s3]"
	@echo ""
	@echo "✅ Installation complete (with S3 support)!"
	@echo "   Activate with: source .venv/bin/activate"
	@echo ""

test:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Copy .env.example and configure it first."; \
		exit 1; \
	fi
	python3 test_config.py

check:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Copy .env.example and configure it first."; \
		exit 1; \
	fi
	python3 publish_pompom_reel.py --check

history:
	python3 publish_pompom_reel.py --history

clean:
	rm -rf .venv
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✅ Cleaned up!"
