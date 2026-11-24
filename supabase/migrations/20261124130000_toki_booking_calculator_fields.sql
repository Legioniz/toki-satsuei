-- TOKI SATSUEI Migration: Add calculator fields to toki_booking_requests and update toki_booking_inbox
-- Integrates calculator package, participants, additional edited photos, and additional session time.

-- 1. Add calculator addon columns to toki_booking_requests
ALTER TABLE public.toki_booking_requests
  ADD COLUMN IF NOT EXISTS additional_photos integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS additional_time integer DEFAULT 0;

-- 2. Update toki_booking_inbox view to expose the new fields
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
    additional_photos,
    additional_time,
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
