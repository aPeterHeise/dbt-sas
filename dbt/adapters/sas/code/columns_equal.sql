select
    row_count_difference,
    num_mismatched
from (
    select
        table_a.num_rows - table_b.num_rows as row_count_difference
	from
        (select count(*) as num_rows from {{ relation_a }}) as table_a,
	    (select count(*) as num_rows from {{ relation_b }}) as table_b
)
join (
    select
        count(*) as num_mismatched from (
            (select {{ columns }} from {{ relation_a }} except
             select {{ columns }} from {{ relation_b }})
             union all
            (select {{ columns }} from {{ relation_a }} except
             select {{ columns }} from {{ relation_b }})
        )
) on 1=1;
