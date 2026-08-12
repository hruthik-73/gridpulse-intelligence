select
    respondent,
    forecast_coverage_pct

from {{ ref('mart_balancing_authority_performance') }}

where
    forecast_coverage_pct is not null
    and (
        forecast_coverage_pct < 0
        or forecast_coverage_pct > 100
    )
