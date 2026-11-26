ALTER TABLE public.submission_rate_limits
  DROP CONSTRAINT submission_rate_limits_scope_allowlist_check;

ALTER TABLE public.submission_rate_limits
  ADD CONSTRAINT submission_rate_limits_scope_allowlist_check
  CHECK (scope = ANY (ARRAY[
    'inquiry'::text,
    'comment'::text,
    'page_view'::text,
    'toki_booking'::text,
    'toki_calendar'::text,
    'toki_booking_contact'::text,
    'toki_gallery_global'::text,
    'toki_gallery_token'::text,
    'portfolio_turnstile_verify'::text
  ]));
