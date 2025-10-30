from setuptools import setup, find_packages

setup(
    name="drone-autonomy",
    version="0.1.0",
    description="Real-time drone autonomy system with monocular vision pipeline",
    author="DroneAutonomy Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "opencv-python>=4.8.0",
        "opencv-contrib-python>=4.8.0",
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "ultralytics>=8.0.0",
        "timm>=0.9.0",
        "pymavlink>=2.4.37",
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "Pillow>=10.0.0",
        "pyyaml>=6.0",
        "tqdm>=4.65.0",
        "colorama>=0.4.6",
    ],
    extras_require={
        "sim": ["airsim"],
        "dev": ["pytest>=7.0.0", "black>=23.0.0", "flake8>=6.0.0"],
    },
)
