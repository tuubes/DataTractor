from setuptools import setup

setup(
	name='DataTractor',
	version='1.1',
	packages=['datatractor', 'datatractor.main', 'datatractor.utils'],
	url='https://github.com/tuubes/DataTractor',
	license='GPLv3',
	author='TheElectronWill',
	description='Data extractor for Tuubes',
	install_requires=['beautifulsoup4', 'requests', 'requests-cache']
)