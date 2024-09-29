{% macro sas__list_relations_without_caching(schema_relation) -%}
'''creates a table of relations withough using local caching.'''
  {% set sql %}
    select
        lower(memname) as memname,
        case when memtype = 'VIEW' then 'view' else 'table' end as type
    from sashelp.vmember
    where (memtype = 'DATA' or memtype = 'VIEW') and libname = '{{ schema_relation.libname }}';
  {% endset %}
  {{ return(run_query(sql)) }}
{% endmacro %}

{% macro sas__list_schemas(database) -%}
'''Returns a table of unique schemas.'''
  {% set sql %}
    select distinct lower(libname) as libname from sashelp.vmember;
  {% endset %}
  {{ return(run_query(sql)) }}
{% endmacro %}

{% macro sas__get_columns_in_relation(relation) -%}
'''Returns a list of Columns in a table.'''
  {% set sql %}
    select lower(name) as name, type, length
    from sashelp.vcolumn
    where libname='{{ relation.libname }}' and memname='{{ relation.dataset }}';
  {% endset %}
  {{ return(run_query(sql)) }}
{% endmacro %}

{% macro sas__check_schema_exists(information_schema,schema) -%}
'''Checks if schema name exists and returns number or times it shows up.'''
  {% set sql %}
    select count(1) from sashelp.vlibnam where libname='{{ schema.upper() }}';
  {% endset %}
  {{ return(run_query(sql)) }}
{% endmacro %}

{% macro sas__make_temp_relation(base_relation, suffix) %}
  {{ return(base_relation.incorporate(path={"schema": none, "database": none})) }}
{% endmacro %}

{% macro sas__alter_column_type(relation,column_name,new_column_type) -%}
'''Changes column name or data type'''
  {#
    1. Create a new temp column with the correct type
    2. Copy data over to it
    3. Drop the existing column
    4. Create a column with the correct name/type
    5. Copy data over to it
    6. Drop the temp column
  #}
  {%- set tmp_column = column_name + "__dbt_alter" -%}

  {% call statement('alter_column_type') %}
    alter table {{ relation }} add {{ tmp_column }} {{ new_column_type }};
    update {{ relation }} set {{ tmp_column }} = {{ column_name }};
    alter table {{ relation }} drop {{ column_name }};
    alter table {{ relation }} add {{ column_name }} {{ new_column_type }};
    update {{ relation }} set {{ column_name }} = {{ tmp_column }};
    alter table {{ relation }} drop {{ tmp_column_name }};
  {% endcall %}
{% endmacro %}

/*
--------------- TODO -----------------------
*/


--  Example from postgres adapter in dbt-core
--  Notice how you can build out other methods than the designated ones for the impl.py file,
--  to make a more robust adapter. ex. (verify_database)

/*


/*

Example 3 of 3 of required macros that does not have a default implementation.
 ** Good example of building out small methods ** please refer to impl.py for implementation of now() in postgres plugin
{% macro postgres__current_timestamp() -%}
  now()
{%- endmacro %}

*/

{% macro sas__current_timestamp() -%}
'''Returns current UTC time'''
{# docs show not to be implemented currently. #}
{% endmacro %}
