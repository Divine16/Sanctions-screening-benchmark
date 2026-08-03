.PHONY: test demo classes generate clean

test:
	python3 -m unittest discover -s tests -t . -v

demo:
	PYTHONPATH=src python3 -m ssb.cli demo

classes:
	PYTHONPATH=src python3 -m ssb.cli classes

generate:
	PYTHONPATH=src python3 -m ssb.cli generate --limit 500 --out benchmark.json

clean:
	rm -f benchmark.json scorecard.json
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
