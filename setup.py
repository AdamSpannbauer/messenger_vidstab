from setuptools import setup

setup(name='vidstabFB',
      version='0.1.0',
      description='Utils for FB Messenger vidstab bot',
      author='Adam Spannbauer',
      author_email='spannbaueradam@gmail.com',
      url='https://github.com/AdamSpannbauer/messenger_vidstab',
      packages=['vidstabFB'],
      license='MIT',
      install_requires=[
          'urllib3',
          'vidstab',
          'requests',
      ]
      )
