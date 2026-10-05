SELECT
  date_parse(billing_period, '%Y-%m')                     AS billing_month,
  CAST(line_item_usage_start_date AS date)                AS usage_date,
  regexp_extract(line_item_iam_principal, '[^/]+$')       AS user_name,
  regexp_extract(line_item_iam_principal, 'assumed-role/([^/]+)/', 1) AS role_name,
  regexp_extract(line_item_resource_id, '[^/]+$')         AS model_id,
  CASE
    WHEN regexp_replace(lower(line_item_usage_type), '[-_]', '') LIKE '%cacheread%'  THEN 'cache_read'
    WHEN regexp_replace(lower(line_item_usage_type), '[-_]', '') LIKE '%cachewrite%' THEN 'cache_write'
    WHEN lower(line_item_usage_type) LIKE '%input%'  THEN 'input'
    WHEN lower(line_item_usage_type) LIKE '%output%' THEN 'output'
    ELSE 'other'
  END                                                     AS token_kind,
  sum(line_item_usage_amount * CASE pricing_unit
        WHEN '1M tokens' THEN 1000000
        WHEN '1K tokens' THEN 1000
        ELSE 1 END)                                       AS tokens,
  sum(line_item_unblended_cost)                           AS cost_usd
FROM cur.cur2
WHERE line_item_iam_principal IS NOT NULL
  AND line_item_iam_principal <> ''
  AND line_item_line_item_type = 'Usage'
GROUP BY 1, 2, 3, 4, 5, 6
