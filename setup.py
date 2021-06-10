import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="grafana-k8s",
    version="2.0.0",
    author="Ryan Barry",
    author_email="ryan.barrycanonical.com",
    description="Kubernetes Charm/Operator for Grafana-k8s",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rbarry82/grafana-operator",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
)
