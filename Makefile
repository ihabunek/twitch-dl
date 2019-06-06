default : clean dist

dist :
	python setup.py sdist --formats=gztar,zip
	python setup.py bdist_wheel

clean :
	find . -name "*pyc" | xargs rm -rf $1
	rm -rf build dist MANIFEST htmlcov deb_dist twitch-dl*.tar.gz twitch-dl.1.man

publish :
	twine upload dist/*.tar.gz dist/*.whl

coverage:
	py.test --cov=toot --cov-report html tests/

deb:
	@python setup.py --command-packages=stdeb.command bdist_deb

man:
	scdoc < twitch-dl.1.scd > twitch-dl.1.man
