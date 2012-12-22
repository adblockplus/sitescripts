DROP TABLE IF EXISTS crawler_sites;
DROP TABLE IF EXISTS crawler_runs;
DROP TABLE IF EXISTS crawler_requests;

CREATE TABLE crawler_sites (
       id INT NOT NULL AUTO_INCREMENT,
       PRIMARY KEY (id),
       url VARCHAR(512) NOT NULL,
       UNIQUE (url)
);

CREATE TABLE crawler_runs (
       id INT NOT NULL AUTO_INCREMENT,
       PRIMARY KEY (id),
       timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crawler_requests (
       id INT NOT NULL AUTO_INCREMENT,
       PRIMARY KEY (id),
       run INT NOT NULL,
       FOREIGN KEY (run) REFERENCES crawler_runs (id),
       site INT NOT NULL,
       FOREIGN KEY (site) REFERENCES crawler_sites (id),
       url VARCHAR(512) NOT NULL,
       filtered BOOLEAN NOT NULL
);
