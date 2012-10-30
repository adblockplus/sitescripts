/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `subscriptions` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `url` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` varchar(40) NOT NULL,
  `reports` int(10) unsigned NOT NULL DEFAULT '0',
  `positive` int(10) unsigned NOT NULL DEFAULT '0',
  `negative` int(10) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`)
) DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `reports` (
  `guid` varchar(40) NOT NULL,
  `type` varchar(30) DEFAULT NULL,
  `ctime` datetime NOT NULL,
  `site` varchar(150) DEFAULT NULL,
  `status` text,
  `comment` text,
  `contact` varchar(40) DEFAULT NULL,
  `hasscreenshot` tinyint(1) NOT NULL DEFAULT '0',
  `knownissues` int(10) unsigned NOT NULL DEFAULT '0',
  `dump` mediumblob,
  PRIMARY KEY (`guid`),
  KEY `reports_ctime` (`ctime`),
  KEY `reports_contract` (`contact`),
  CONSTRAINT `reports_contract` FOREIGN KEY (`contact`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sublists` (
  `report` varchar(40) NOT NULL,
  `list` int(10) unsigned NOT NULL,
  `hasmatches` tinyint(1) NOT NULL DEFAULT '0',
  UNIQUE KEY `report_list` (`list`,`report`),
  KEY `sublists_report` (`report`),
  CONSTRAINT `sublists_report` FOREIGN KEY (`report`) REFERENCES `reports` (`guid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `sublists_list` FOREIGN KEY (`list`) REFERENCES `subscriptions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
