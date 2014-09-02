zco.mx
==========

zco.mx code base.

Requirements
------------

[web2py](http://web2py.com "web2py") requires python version 2.5 or later 2.x. 

The following python modules are used.

1. [BeautifulSoup Ver 3](http://www.crummy.com/software/BeautifulSoup/index.html "Beautiful Soup")
2. [Python Imaging Library](http://pythonware.com/products/pil/ "Python Imaging Library (PIL)") or [Pillow](https://github.com/python-imaging/Pillow "Pillow on github.com")


To install with [ArchLinux](http://www.archlinux.org), use the following command.

    $ pacman -S python2-beautifulsoup3 python2-pillow


Configuration
-------------

Copy settings.examples.conf to settings.conf

    $ cp applications/zcomix/private/{settings.example.conf,settings.conf}


Edit the settings as required.

    $ vi applications/zcomix/private/settings.conf


Run
---

Start the web2py server.

    $ cd zcomix.com
    $ SERVER_PRODUCTION_MODE=test python2 web2py.py 

If running on a remote server with ip address 123.123.123.123:

    $ SERVER_PRODUCTION_MODE=test python2 web2py.py -i 123.123.123.123 -p 80
