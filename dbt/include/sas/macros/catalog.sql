{% macro sas__get_catalog(information_schema, schemas) -%}
  {% set query %}
      select
          'sas' as table_database,
          lower(libname) as table_schema,
          lower(memname) as table_name,
          case
              when memtype = 'DATA' then 'BASE TABLE'
              else memtype
          end as table_type,
          '' as table_comment,
          name as column_name,
          npos as column_index,
          type as column_type,
          '' as column_comment,
          '' as table_owner
      from
          sashelp.vcolumn
      where
          ({%- for schema in schemas -%}
               libname = '{{ schema.upper() }}'{%- if not loop.last %} or {% endif -%}
          {%- endfor -%})
    {%- endset -%}
  {{ return(run_query(query)) }}
{%- endmacro %}
