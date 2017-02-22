from setuptools import setup

setup(
    name='microticks',
    packages=['microticks'],
    include_package_data=True,
    install_requires=[
        'pyyaml',
        'flask',
        'Flask-JSON',
        'flask-cors',
        'raven',
        'raven[flask]'
    ],
)
