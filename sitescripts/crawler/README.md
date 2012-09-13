crawler
=======

Backend for the Adblock Plus Crawler. It provides the following URLs:

* */crawlableUrls* - Return a list of sites to be crawled
* */crawlerRun, /crawlerData* - Receive data on filtered elements

Database setup
--------------

Just execute the statements in _schema.sql_.

Configuration
-------------

Make sure that _database_, _dbuser_ and _dbpassword_ is configured
correctly in _/etc/sitescripts_ or _.sitescripts_.

Then add an empty _crawler_ section.

Extracting crawler sites
------------------------

Make _filter\_list\_repository_ in the _crawler_ configuration section
point to the local Mercurial repository of a filter list.

Then execute the following:

    python -m sitescripts.crawler.bin.extract_crawler_sites > crawler_sites.sql

Now you can execute the insert statements from _crawler\_sites.sql_.
