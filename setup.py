import os
from setuptools import setup, find_packages
import versioneer
import sys

if sys.version_info < (3, 6):
    print("\n")
    print("This requires python 3.6 or higher")
    print("\n")
    raise SystemExit

# https://www.pydanny.com/python-dot-py-tricks.html
if sys.argv[-1] == 'test':
    test_requirements = [
        'pytest',
        'coverage',
        'pytest_cov',
    ]
    try:
        modules = map(__import__, test_requirements)
    except ImportError as e:
        err_msg = e.message.replace("No module named ", "")
        msg = "%s is not installed. Install your test requirements." % err_msg
        raise ImportError(msg)
    r = os.system('pytest test -v --cov=csirtg_fm --cov-fail-under=50')
    if r == 0:
        sys.exit()
    else:
        raise RuntimeError('tests failed')

setup(
    name="csirtg-fm",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="CSIRTG FM Framework",
    long_description="",
    url="https://github.com/csirtgadgets/csirtg-fm-v2",
    license='MPL2',
    classifiers=[
               "Topic :: System :: Networking",
               "Programming Language :: Python",
               ],
    keywords=['security'],
    author="Wes Young",
    author_email="wes@csirtgadgets.com",
    packages=find_packages(exclude=["test"]),
    install_requires=[
        'prettytable',
        'feedparser',
        'requests',
        'python-magic',
        'arrow',
        'csirtg_indicator>=3.0a1,<4.0',
    ],
    scripts=[],
    entry_points={
        'console_scripts': [
            'csirtg-fm=csirtg_fm.cli:main',
        ]
    },
)
