python=/usr/bin/env python3


test:
	echo && PYTHONPATH="${PYTHONPATH}:twisted_mtr" $(python) -m unittest discover -s tests -v
