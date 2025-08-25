from setuptools import setup, find_packages

package_name = 'aqua_feeder'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/aqua_feeder_launch.py']),
        ('share/' + package_name + '/config', ['config/system_params.yaml']),
    ],
    install_requires=[
        'setuptools',
        'opencv-python>=4.5.0',
        'numpy>=1.19.0',
        'scipy>=1.6.0',
        'matplotlib>=3.3.0',
        'pyyaml>=5.4.0',
        'scikit-image>=0.18.0',
        'jetson-gpio',
    ],
    zip_safe=True,
    maintainer='aqua-feeder-team',
    maintainer_email='team@aquafeeder.com',
    description='智能水產養殖自動餵料控制系統',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vision_node = aqua_feeder.vision.vision_node:main',
            'control_node = aqua_feeder.control.control_node:main',
            'hardware_node = aqua_feeder.hardware.hardware_node:main',
            'main_controller = aqua_feeder.main_controller:main',
        ],
    },
)
