from setuptools import setup, find_packages

setup(
    name="apiofdreams",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pymongo",
        "langchain",
        "langchain_openai",
        "langgraph",
        "mangum",
        # Add any other dependencies your project needs
    ],
)
