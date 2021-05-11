import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="grafana-charm",
    version="0.0.1",
    author="Ryan Barry",
    author_email="ryan.barrycanonical.com",
    description="Kubernetes Charm/Operator for Grafana",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rbarry82/grafana-charm",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
)
