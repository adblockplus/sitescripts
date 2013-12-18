crawler
=======

Backend for the Adblock Plus Crawler. It provides the following URLs:

* */crawlableSites* - Return a list of sites to be crawled
* */crawlerRequests* - Receive all requests made, and whether they were filtered

Required packages
-----------------

* [MySQL-Python](http://mysql-python.sourceforge.net/)

Database setup
--------------

Just execute the statements in _schema.sql_.

Configuration
-------------

Just add an empty _crawler_ section to _/etc/sitescripts_ or _.sitescripts_.

If you want to import crawlable sites from easylist (see below), you
need to make _easylist\_repository_ point to the local Mercurial
repository of easylist.

Also make sure that the following keys are configured in the _DEFAULT_
section:

* _database_
* _dbuser_
* _dbpassword_
* _basic\_auth\_realm_
* _basic\_auth\_username_
* _basic\_auth\_password_

Importing crawlable sites from easylist
---------------------------------------

    python -m sitescripts.crawler.bin.import_sites
