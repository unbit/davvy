from setuptools import setup, find_packages

setup(
    author="Unbit",
    author_email="info@unbit.com",
    name='davvy',
    version='0.1',
    description='A Django application for building WebDAV services',
    url="https://github.com/unbit/davvy",
    license='MIT License',
    install_requires=[
        'django',
        'lxml',
    ],
    packages=find_packages(),
)
