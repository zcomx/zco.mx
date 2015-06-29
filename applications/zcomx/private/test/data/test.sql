/* SQL queries used to set up for unittests. */
DELETE FROM job;
CREATE TABLE test__reorder(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name CHAR(512),
    order_no INTEGER,
    created_on TIMESTAMP,
    updated_on TIMESTAMP
);
