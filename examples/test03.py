import logging

try:
	create_external('xml2', build_helper = 'xml2-config',
		version_query = '--version', version_parser = lambda x: 'invalid')
except Exception:
	logging.critical('external version parsing')

try:
	tools['c'].std = 'latest'
except Exception:
	logging.critical('std setting')

try:
	shared_library('x', [])
except Exception:
	logging.critical('shared_library: empty input')

try:
	static_library('x', [])
except Exception:
	logging.critical('static_library: empty input')
