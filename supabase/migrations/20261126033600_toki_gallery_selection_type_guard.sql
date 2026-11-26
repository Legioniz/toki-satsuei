CREATE OR REPLACE FUNCTION private.toki_submit_client_selection(p_token text, p_selections jsonb)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
  v_token_hash text;
  v_global_hash text := pg_catalog.encode(extensions.digest('toki-gallery-global-v1', 'sha256'), 'hex');
  v_booking_id uuid;
  v_selection_count integer;
  v_distinct_count integer;
BEGIN
  IF p_token IS NULL OR p_token !~ '^toki-[0-9a-f]{64}$' THEN
    RETURN pg_catalog.json_build_object('ok', false, 'message', 'Unable to save selections. The gallery may have expired or been revoked.');
  END IF;

  v_token_hash := pg_catalog.encode(extensions.digest(p_token, 'sha256'), 'hex');

  SELECT id
  INTO v_booking_id
  FROM public.toki_booking_requests
  WHERE delivery_token_hash = v_token_hash
    AND delivery_status IN ('ready', 'delivered')
    AND delivery_folder_url IS NOT NULL
    AND delivery_expires_at IS NOT NULL
    AND pg_catalog.clock_timestamp() < delivery_expires_at;

  IF v_booking_id IS NULL THEN
    RETURN pg_catalog.json_build_object('ok', false, 'message', 'Unable to save selections. The gallery may have expired or been revoked.');
  END IF;

  -- Validate JSON shape before calling array-only functions. Keep these as
  -- separate PL/pgSQL branches so malformed objects never reach array_length.
  IF p_selections IS NULL THEN
    RETURN pg_catalog.json_build_object('ok', false, 'message', 'Selections must be a list of up to 50 photo IDs.');
  END IF;

  IF pg_catalog.jsonb_typeof(p_selections) IS DISTINCT FROM 'array' THEN
    RETURN pg_catalog.json_build_object('ok', false, 'message', 'Selections must be a list of up to 50 photo IDs.');
  END IF;

  IF pg_catalog.jsonb_array_length(p_selections) > 50 THEN
    RETURN pg_catalog.json_build_object('ok', false, 'message', 'Selections must be a list of up to 50 photo IDs.');
  END IF;

  SELECT pg_catalog.count(*), pg_catalog.count(DISTINCT selected.value #>> '{}')
  INTO v_selection_count, v_distinct_count
  FROM pg_catalog.jsonb_array_elements(p_selections) AS selected(value)
  WHERE pg_catalog.jsonb_typeof(selected.value) = 'string'
    AND pg_catalog.char_length(selected.value #>> '{}') BETWEEN 1 AND 128;

  IF v_selection_count <> pg_catalog.jsonb_array_length(p_selections)
     OR v_distinct_count <> v_selection_count THEN
    RETURN pg_catalog.json_build_object('ok', false, 'message', 'The selection list contains invalid or duplicate photo IDs.');
  END IF;

  IF NOT public.consume_portfolio_quota(v_token_hash, 'toki_gallery_token', 10) THEN
    RETURN pg_catalog.json_build_object('ok', false, 'code', 'rate_limited', 'message', 'Too many attempts for this access key. Please retry later.');
  END IF;

  IF NOT public.consume_portfolio_quota(v_global_hash, 'toki_gallery_global', 120) THEN
    RETURN pg_catalog.json_build_object('ok', false, 'code', 'rate_limited', 'message', 'Too many gallery requests. Please retry later.');
  END IF;

  UPDATE public.toki_booking_requests
  SET client_selected_photos = p_selections,
      client_selection_submitted_at = pg_catalog.clock_timestamp(),
      updated_at = pg_catalog.clock_timestamp()
  WHERE id = v_booking_id
    AND delivery_token_hash = v_token_hash
    AND delivery_status IN ('ready', 'delivered')
    AND delivery_folder_url IS NOT NULL
    AND delivery_expires_at IS NOT NULL
    AND pg_catalog.clock_timestamp() < delivery_expires_at;

  IF FOUND THEN
    RETURN pg_catalog.json_build_object('ok', true, 'message', 'Selections saved successfully.');
  END IF;

  RETURN pg_catalog.json_build_object('ok', false, 'message', 'Unable to save selections. The gallery may have expired or been revoked.');
END;
$function$;
