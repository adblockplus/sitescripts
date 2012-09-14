crawler
=======

Backend for the Adblock Plus Crawler. It provides the following URLs:

* */crawlableSites* - Return a list of sites to be crawled
* */crawlerData* - Receive data on filtered elements

Required packages
-----------------

* [simplejson](http://pypi.python.org/pypi/simplejson/)

Database setup
--------------

Just execute the statements in _schema.sql_.

Configuration
-------------

Just add an empty _crawler_ section to _/etc/sitescripts_ or _.sitescripts_.

Also make sure that the following keys are configured in the _DEFAULT_
section:

* _database_
* _dbuser_
* _dbpassword_
* _basic\_auth\_realm_
* _basic\_auth\_username_
* _basic\_auth\_password_

Extracting crawler sites
------------------------

Make _filter\_list\_repository_ in the _crawler_ configuration section
point to the local Mercurial repository of a filter list.

Then execute the following:

    python -m sitescripts.crawler.bin.extract_crawler_sites > crawler_sites.sql

Now you can execute the insert statements from _crawler\_sites.sql_.
