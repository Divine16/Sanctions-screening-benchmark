.PHONY: test demo classes generate compare sweep clean

test:
	python3 -m unittest discover -s tests -t . -v

demo:
	PYTHONPATH=src python3 -m ssb.cli demo

classes:
	PYTHONPATH=src python3 -m ssb.cli classes

generate:
	PYTHONPATH=src python3 -m ssb.cli generate --limit 500 --out benchmark.json

compare:
	PYTHONPATH=src python3 -m ssb.cli generate --offline --limit 10 --max-per-class 1 --out /tmp/ssb-bench.json
	PYTHONPATH=src python3 -m ssb.cli compare /tmp/ssb-bench.json --a exact --b baseline

sweep:
	PYTHONPATH=src python3 -m ssb.cli generate --offline --limit 10 --max-per-class 1 --out /tmp/ssb-bench.json
	PYTHONPATH=src python3 -m ssb.cli sweep /tmp/ssb-bench.json --from-threshold 0.7 --to-threshold 0.95 --step 0.05

clean:
	rm -f benchmark.json scorecard.json
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
