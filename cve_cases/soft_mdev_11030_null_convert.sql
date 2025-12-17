-- MDEV-11030: MariaDB heap buffer overflow converting NULL to integer
-- Pattern 2.1: Boundary type casting with NULL
SELECT * FROM (SELECT IFNULL(CONVERT(NULL, UNSIGNED), NULL)) sq;
SELECT CAST(NULL AS UNSIGNED);
SELECT CONVERT(NULL, SIGNED);
