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
    admin_notes AS private_admin_notes,
    updated_at AS last_updated,
    booking_terms_version,
    booking_terms_accepted_at
   FROM public.toki_booking_requests;
