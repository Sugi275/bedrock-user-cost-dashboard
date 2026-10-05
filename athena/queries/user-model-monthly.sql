WITH t AS (
  SELECT billing_period,
         regexp_extract(line_item_iam_principal, '[^/]+$') AS user_name,
         regexp_extract(line_item_resource_id, '[^/]+$')   AS model_id,
         CASE
           WHEN regexp_replace(lower(line_item_usage_type), '[-_]', '') LIKE '%cacheread%'  THEN 'cache_read'
           WHEN regexp_replace(lower(line_item_usage_type), '[-_]', '') LIKE '%cachewrite%' THEN 'cache_write'
           WHEN lower(line_item_usage_type) LIKE '%input%'  THEN 'input'
           WHEN lower(line_item_usage_type) LIKE '%output%' THEN 'output'
           ELSE 'other'
         END AS kind,
         line_item_unblended_cost AS cost
  FROM cur.cur2
  WHERE line_item_iam_principal IS NOT NULL
    AND line_item_iam_principal <> ''
    AND line_item_line_item_type = 'Usage'
)
SELECT billing_period,
       user_name,
       model_id,
       round(sum(CASE WHEN kind = 'input'       THEN cost ELSE 0 END), 4) AS input_usd,
       round(sum(CASE WHEN kind = 'output'      THEN cost ELSE 0 END), 4) AS output_usd,
       round(sum(CASE WHEN kind = 'cache_write' THEN cost ELSE 0 END), 4) AS cache_write_usd,
       round(sum(CASE WHEN kind = 'cache_read'  THEN cost ELSE 0 END), 4) AS cache_read_usd,
       round(sum(CASE WHEN kind = 'other'       THEN cost ELSE 0 END), 4) AS other_usd,
       round(sum(cost), 4)                                                AS total_usd
FROM t
GROUP BY 1, 2, 3
ORDER BY billing_period DESC, user_name, total_usd DESC;
