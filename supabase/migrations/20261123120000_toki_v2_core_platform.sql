-- TOKI SATSUEI 2.0 Core Platform Migration
-- Extends toki_booking_requests with payment tracking, pricing breakdown, and photo delivery.
-- Creates client selections, verified testimonials, and journal entries with strict RLS.

-- 1. Extend toki_booking_requests
ALTER TABLE public.toki_booking_requests
  ADD COLUMN IF NOT EXISTS total_price numeric(10, 2) DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS reservation_fee numeric(10, 2) DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS reservation_fee_paid boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS reservation_fee_paid_at timestamptz,
  ADD COLUMN IF NOT EXISTS balance_paid boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS balance_paid_at timestamptz,
  ADD COLUMN IF NOT EXISTS add_ons jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS delivery_status text DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS delivery_folder_url text,
  ADD COLUMN IF NOT EXISTS delivery_token text UNIQUE,
  ADD COLUMN IF NOT EXISTS delivery_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS client_selected_photos jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS client_selection_submitted_at timestamptz;

-- 2. Constraints on status
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'toki_booking_delivery_status_check'
  ) THEN
    ALTER TABLE public.toki_booking_requests
      ADD CONSTRAINT toki_booking_delivery_status_check
      CHECK (delivery_status IN ('pending', 'editing', 'ready', 'delivered', 'revoked', 'expired'));
  END IF;
END $$;

-- 3. Update toki_booking_inbox view
CREATE OR REPLACE VIEW public.toki_booking_inbox
WITH (security_invoker = true)
AS
  SELECT
    id AS booking_id,
    reference_code,
    status,
    created_at AS submitted_at,
    name AS client_name,
    contact_method,
    contact_value,
    session_type,
    preferred_date AS requested_date,
    alternate_date,
    preferred_time AS requested_time,
    requested_time_of_day_legacy AS legacy_requested_time_of_day,
    location,
    participants,
    notes AS client_notes,
    privacy_consent,
    confirmed_date,
    confirmed_start_time,
    confirmed_end_time,
    total_price,
    reservation_fee,
    reservation_fee_paid,
    reservation_fee_paid_at,
    balance_paid,
    balance_paid_at,
    add_ons,
    delivery_status,
    delivery_folder_url,
    delivery_token,
    delivery_expires_at,
    client_selected_photos,
    client_selection_submitted_at,
    admin_notes AS private_admin_notes,
    updated_at AS last_updated,
    booking_terms_version,
    booking_terms_accepted_at
  FROM public.toki_booking_requests;

-- 4. Create toki_journal_entries table
CREATE TABLE IF NOT EXISTS public.toki_journal_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text UNIQUE NOT NULL,
  title text NOT NULL,
  kicker text NOT NULL,
  summary text NOT NULL,
  content text NOT NULL,
  cover_image_url text,
  tags text[] DEFAULT '{}'::text[],
  published boolean DEFAULT true,
  published_at timestamptz DEFAULT clock_timestamp(),
  created_at timestamptz DEFAULT clock_timestamp()
);

ALTER TABLE public.toki_journal_entries ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'toki_journal_entries' AND policyname = 'Public can view published journal entries'
  ) THEN
    CREATE POLICY "Public can view published journal entries"
      ON public.toki_journal_entries FOR SELECT
      TO anon, authenticated
      USING (published = true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'toki_journal_entries' AND policyname = 'Public can view published journal entries'
  ) THEN
    CREATE POLICY "Public can view published journal entries"
      ON public.toki_journal_entries FOR SELECT
      TO anon, authenticated
      USING (published = true);
  END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS private;

CREATE OR REPLACE FUNCTION private.is_portfolio_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.admin_users AS allowed_admin
    WHERE allowed_admin.user_id = (SELECT auth.uid())
  );
$$;

REVOKE ALL ON FUNCTION private.is_portfolio_admin() FROM PUBLIC, anon;
GRANT USAGE ON SCHEMA private TO authenticated;
GRANT EXECUTE ON FUNCTION private.is_portfolio_admin() TO authenticated;

DROP POLICY IF EXISTS "Admins manage journal entries" ON public.toki_journal_entries;
CREATE POLICY "Admins manage journal entries"
  ON public.toki_journal_entries FOR ALL
  TO authenticated
  USING ((SELECT private.is_portfolio_admin()))
  WITH CHECK ((SELECT private.is_portfolio_admin()));

-- 6. Function for client delivery lookup & selection submission
CREATE OR REPLACE FUNCTION public.toki_get_client_gallery(p_token text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_result json;
BEGIN
  IF p_token IS NULL OR char_length(trim(p_token)) < 8 THEN
    RETURN json_build_object('ok', false, 'message', 'Invalid access token.');
  END IF;

  SELECT json_build_object(
    'ok', true,
    'reference_code', reference_code,
    'client_name', name,
    'session_type', session_type,
    'confirmed_date', confirmed_date,
    'delivery_status', delivery_status,
    'delivery_folder_url', delivery_folder_url,
    'delivery_expires_at', delivery_expires_at,
    'client_selected_photos', client_selected_photos,
    'client_selection_submitted_at', client_selection_submitted_at
  ) INTO v_result
  FROM public.toki_booking_requests
  WHERE delivery_token = trim(p_token)
    AND delivery_status IN ('ready', 'delivered')
    AND delivery_folder_url IS NOT NULL
    AND (delivery_expires_at IS NULL OR clock_timestamp() <= delivery_expires_at);

  IF v_result IS NULL THEN
    RETURN json_build_object('ok', false, 'message', 'Gallery not found or access has been revoked.');
  END IF;

  RETURN v_result;
END;
$$;

GRANT EXECUTE ON FUNCTION public.toki_get_client_gallery(text) TO anon, authenticated;

CREATE OR REPLACE FUNCTION public.toki_submit_client_selection(p_token text, p_selections jsonb)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_updated boolean;
BEGIN
  IF p_token IS NULL OR char_length(trim(p_token)) < 8 THEN
    RETURN json_build_object('ok', false, 'message', 'Invalid access token.');
  END IF;

  IF p_selections IS NULL OR jsonb_typeof(p_selections) <> 'array' THEN
    RETURN json_build_object('ok', false, 'message', 'Selections must be a list of photo IDs.');
  END IF;

  IF jsonb_array_length(p_selections) > 50 OR EXISTS (
    SELECT 1
    FROM jsonb_array_elements(p_selections) AS selected(value)
    WHERE jsonb_typeof(selected.value) <> 'string'
       OR char_length(selected.value #>> '{}') NOT BETWEEN 1 AND 128
  ) THEN
    RETURN json_build_object('ok', false, 'message', 'The selection list contains too many or invalid photo IDs.');
  END IF;

  UPDATE public.toki_booking_requests
  SET
    client_selected_photos = p_selections,
    client_selection_submitted_at = clock_timestamp(),
    updated_at = clock_timestamp()
  WHERE delivery_token = trim(p_token)
    AND delivery_status IN ('ready', 'delivered')
    AND delivery_folder_url IS NOT NULL
    AND (delivery_expires_at IS NULL OR clock_timestamp() <= delivery_expires_at);

  IF FOUND THEN
    RETURN json_build_object('ok', true, 'message', 'Selections saved successfully.');
  ELSE
    RETURN json_build_object('ok', false, 'message', 'Unable to save selections. The gallery may have expired or been revoked.');
  END IF;
END;
$$;

GRANT EXECUTE ON FUNCTION public.toki_submit_client_selection(text, jsonb) TO anon, authenticated;
