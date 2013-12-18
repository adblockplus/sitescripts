urlfixer
========

Backend for the URL Fixer data collection. It provides the following URLs:

* */submitData* - Receive data from URL Fixer extension

Required packages
-----------------

* [MySQL-Python](http://mysql-python.sourceforge.net/)

Database setup
--------------

Just execute the statements in _schema.sql_.

Configuration
-------------

Add an _urlfixer_ section to _/etc/sitescripts_ or _.sitescripts_ and configure the following keys:

* _database_
* _dbuser_
* _dbpassword_

Data transfer format
----------------------------

A domain transfered to the server can have one of the following types:

* 1: the domain was entered without any further action
* 2: the domain was recognized as a typo
* 3: the domain is a correction that the user accepted
* 4: the domain is a correction that the user declined

The server expects the list to be transfered as a JSON object in no particular order. Here is an example:

```js
{
  "urlfixer.org": 1,
  "adblockplus,org": 2,
  "adblockplus.org": 3,
  "goggle.com": 1,
  "google.com": 4
}
```
