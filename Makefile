.PHONY: docs

default : clean dist

dist:
	python -m build

clean :
	find . -name "*pyc" | xargs rm -rf $1
	rm -rf build dist book bundle MANIFEST htmlcov deb_dist twitch-dl.*.pyz twitch-dl.1.man twitch_dl.egg-info

bundle:
	mkdir bundle
	cp twitchdl/__main__.py bundle
	pip install . --target=bundle
	rm -rf bundle/*.dist-info
	find bundle/ -type d -name "__pycache__" -exec rm -rf {} +
	python -m zipapp \
		--python "/usr/bin/env python3" \
		--output twitch-dl.`git describe`.pyz bundle \
		--compress

publish :
	twine upload dist/*.tar.gz dist/*.whl

coverage:
	pytest --cov=twitchdl --cov-report html tests/

man:
	scdoc < twitch-dl.1.scd > twitch-dl.1.man

test:
	pytest

changelog:
	./scripts/generate_changelog > CHANGELOG.md

docs: changelog
	python scripts/generate_docs
	mdbook build

docs-serve:
	python scripts/generate_docs
	mdbook serve --port 8000

docs-deploy: docs
	rsync --archive --compress --delete --stats book/ bezdomni:web/twitch-dl
