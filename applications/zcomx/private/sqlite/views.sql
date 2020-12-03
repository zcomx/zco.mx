DROP VIEW IF EXISTS creator_grid_v;
CREATE VIEW IF NOT EXISTS creator_grid_v AS
    SELECT
        c.id as creator_id,
        sum(CASE WHEN b.release_date IS NOT NULL THEN 1 ELSE 0 END) as completed,
        sum(CASE WHEN b.release_date IS NULL THEN 1 ELSE 0 END) as ongoing,
        sum(b.downloads) as downloads,
        sum(b.views) as views,
        c.created_on as created_on,
        c.updated_on as updated_on
    FROM creator c
    LEFT JOIN book b ON b.creator_id=c.id
    GROUP BY c.id
;
