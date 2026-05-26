*********************
Django file Captcha
*********************

.. image:: https://github.com/mbi/django-file-captcha/actions/workflows/test.yml/badge.svg
  :target: https://github.com/mbi/django-file-captcha/actions/workflows/test.yml

.. image:: https://img.shields.io/pypi/v/django-file-captcha
  :target: https://pypi.org/project/django-file-captcha/

.. image:: https://img.shields.io/pypi/l/django-file-captcha
  :target: https://github.com/mbi/django-file-captcha/blob/master/LICENSE


Django File Captcha is an extremely file, yet highly customizable Django application to add captcha images to any Django form.

.. image:: http://django-file-captcha.readthedocs.io/en/latest/_images/captcha3.png

Features
++++++++

* Very file to setup and deploy, yet very configurable
* Can use custom challenges (e.g. random chars, file math, dictionary word, ...)
* Custom generators, noise and filter functions alter the look of the generated image
* Supports text-to-speech audio output of the challenge text, for improved accessibility
* Ajax refresh

Requirements
++++++++++++

* Django 4.2+, Python3.8+
* A recent version of the Pillow compiled with FreeType support
* Flite is required for text-to-speech (audio) output, but not mandatory

Documentation
+++++++++++++

Read the `documentation online <http://django-file-captcha.readthedocs.org/en/latest/>`_.
