from setuptools import setup, find_packages

setup(
    name="christman-voice-sdk",
    version="1.0.0",
    author="Everett Nathaniel Christman",
    author_email="lumacognify@thechristmanaiproject.com",
    description="The Christman Voice SDK — complete voice intelligence package",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "numpy",
        "librosa",
        "soundfile",
        "torch",
        "torchaudio",
        "transformers",
        "pygame",
        "gtts",
        "pyttsx3",
        "flask",
        "fastapi",
        "rich",
        "parselmouth",
    ],
)
