with aggregate_respondents as (

    select respondent
    from {{ ref('eia_respondent_types') }}

),

invalid as (

    select
        performance.respondent

    from {{ ref('mart_balancing_authority_performance') }}
        as performance

    inner join aggregate_respondents
        on performance.respondent
            = aggregate_respondents.respondent

)

select *
from invalid
