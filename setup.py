from setuptools import setup

setup(
    name='microticks',
    packages=['microticks'],
    include_package_data=True,
    install_requires=[
        'pyyaml',
        'flask',
        'flask-json',
        'flask-cors',
        'flask-log',
        'raven',
        'raven[flask]',
        'gunicorn'
    ],
)
