CREATE OR REPLACE FUNCTION public.consume_portfolio_quota(
  p_bucket_hash text,
  p_scope text,
  p_limit integer DEFAULT 5
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
  v_now timestamptz := pg_catalog.clock_timestamp();
  v_window timestamptz;
  v_scope_ceiling integer;
  v_count integer;
BEGIN
  IF p_bucket_hash IS NULL OR p_bucket_hash !~ '^[0-9a-f]{64}$' THEN
    RAISE EXCEPTION 'Invalid quota bucket hash' USING ERRCODE = '22023';
  END IF;

  v_scope_ceiling := CASE p_scope
    WHEN 'inquiry' THEN 4
    WHEN 'comment' THEN 6
    WHEN 'page_view' THEN 60
    WHEN 'toki_booking' THEN 4
    WHEN 'toki_calendar' THEN 30
    WHEN 'toki_booking_contact' THEN 2
    WHEN 'toki_gallery_global' THEN 120
    WHEN 'toki_gallery_token' THEN 10
    WHEN 'portfolio_turnstile_verify' THEN 20
    ELSE NULL
  END;

  IF v_scope_ceiling IS NULL THEN
    RAISE EXCEPTION 'Invalid quota scope' USING ERRCODE = '22023';
  END IF;
  IF p_limit IS NULL OR p_limit < 1 OR p_limit > v_scope_ceiling THEN
    RAISE EXCEPTION 'Requested quota exceeds the scope ceiling' USING ERRCODE = '22023';
  END IF;

  v_window := pg_catalog.to_timestamp(pg_catalog.floor(extract(epoch FROM v_now) / 600) * 600);

  IF mod(extract(minute FROM v_now)::integer, 10) = 0
     AND extract(second FROM v_now) < 5 THEN
    DELETE FROM public.submission_rate_limits WHERE expires_at < v_now;
  END IF;

  INSERT INTO public.submission_rate_limits (bucket_hash, scope, window_start, hit_count, expires_at)
  VALUES (p_bucket_hash, p_scope, v_window, 1, v_now + interval '2 days')
  ON CONFLICT (bucket_hash, scope, window_start)
  DO UPDATE SET
    hit_count = CASE
      WHEN public.submission_rate_limits.hit_count < 2147483647
        THEN public.submission_rate_limits.hit_count + 1
      ELSE public.submission_rate_limits.hit_count
    END,
    expires_at = EXCLUDED.expires_at
  RETURNING hit_count INTO v_count;

  RETURN v_count <= p_limit;
END;
$function$;
