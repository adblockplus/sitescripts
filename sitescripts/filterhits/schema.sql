/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `filters` (
  `sha1` BINARY(20) NOT NULL,
  `filter` TEXT CHARACTER SET utf8 NOT NULL,
  PRIMARY KEY(sha1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

CREATE TABLE `frequencies` (
  `filter_sha1` BINARY(20) NOT NULL,
  `domain` varchar(255) CHARACTER SET utf8 NOT NULL,
  `frequency` int(10) unsigned DEFAULT 0 NOT NULL,
  `timestamp` timestamp NOT NULL,
  PRIMARY KEY(domain, filter_sha1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
/*!40101 SET character_set_client = @saved_cs_client */;
