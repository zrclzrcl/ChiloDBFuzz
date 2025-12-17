-- MDEV-8407: MariaDB heap buffer overflow converting large decimal to string
-- Pattern 2.1: Boundary type casting (60-digit decimal)
SELECT COLUMN_JSON(COLUMN_CREATE('x', 123456789012345678901234567890123456789012345678901234567890));
