/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `report_reports` (
  `guid` varchar(40) NOT NULL,
  `type` varchar(30) NOT NULL,
  `ctime` datetime NOT NULL,
  `site` varchar(150) DEFAULT NULL,
  `dump` mediumblob,
  PRIMARY KEY (`guid`),
  KEY `reports_ctime` (`ctime`)
) DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `report_sublists` (
  `report` varchar(40) NOT NULL,
  `list` int(10) unsigned NOT NULL,
  UNIQUE KEY `report_list` (`list`,`report`),
  KEY `report_sublists_ibfk_1` (`report`),
  CONSTRAINT `report_sublists_ibfk_1` FOREIGN KEY (`report`) REFERENCES `report_reports` (`guid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `report_sublists_ibfk_2` FOREIGN KEY (`list`) REFERENCES `report_subscriptions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `report_subscriptions` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `url` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
