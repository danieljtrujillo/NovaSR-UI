from setuptools import setup, find_packages

setup(
    name='NovaSR',
    version='0.0.2',
    packages=find_packages(),
    author='ysharma3501',
    description='A fast, small, and high-quality neural audio upsampling model.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/ysharma3501/NovaSR',
    license='MIT',
    install_requires=[
        'soxr>=0.3.0',
        'soundfile>=0.12.0',
        'timm>=0.9.0',
        'torchaudio>=2.0.0',
        'torch>=2.0.0',
        'einops>=0.6.0',
        'huggingface_hub>=0.16.0',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.9',
)
