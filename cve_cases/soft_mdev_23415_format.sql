-- MDEV-23415: MariaDB heap buffer overflow in FORMAT function
-- Pattern 1.1: Boundary literal value (decimal digits > 31)
SELECT FORMAT('0', 50, 'de_DE');
SELECT FORMAT(1.0, 50);
SELECT FORMAT(1.0, 2147483647);
