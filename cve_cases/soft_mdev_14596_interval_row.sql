-- MDEV-14596: MariaDB segmentation violation on ROW type in INTERVAL
-- Pattern 3.3: Nested function with incompatible types
SELECT INTERVAL(ROW(1,1), ROW(1,2));
SELECT INTERVAL(N, ROW(1,1), ROW(1,2));
