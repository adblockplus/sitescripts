DROP TABLE IF EXISTS domains;
DROP TABLE IF EXISTS corrections;

CREATE TABLE domains(
  id INT NOT NULL AUTO_INCREMENT,
  domain VARCHAR(50) NOT NULL,
  PRIMARY KEY(id),
  UNIQUE(domain)
);

CREATE TABLE corrections(
  id INT NOT NULL AUTO_INCREMENT,
  domain INT NOT NULL,
  status INT NOT NULL,
  curr_month INT NOT NULL,
  prev_month INT NOT NULL,
  curr_year INT NOT NULL,
  prev_year INT NOT NULL,
  PRIMARY KEY(id),
  FOREIGN KEY(domain) REFERENCES domains(id),
  UNIQUE(domain, status)
);
