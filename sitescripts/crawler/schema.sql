DROP TABLE IF EXISTS crawler_sites;
DROP TABLE IF EXISTS crawler_runs;
DROP TABLE IF EXISTS crawler_data;

CREATE TABLE crawler_sites (
       id INT NOT NULL AUTO_INCREMENT,
       PRIMARY KEY (id),
       url VARCHAR(512) NOT NULL
);

CREATE TABLE crawler_runs (
       id INT NOT NULL AUTO_INCREMENT,
       PRIMARY KEY (id),
       timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crawler_data (
       id INT NOT NULL AUTO_INCREMENT,
       PRIMARY KEY (id),
       run INT NOT NULL,
       FOREIGN KEY (run) REFERENCES crawler_runs (id),
       site INT NOT NULL,
       FOREIGN KEY (site) REFERENCES crawler_sites (id),
       url VARCHAR(512) NOT NULL,
       filtered BOOLEAN NOT NULL
);
