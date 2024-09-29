{% macro sas__load_csv_rows(model, agate_table) %}
  {% do adapter.import_seed(agate_table, this) %}
  {# Return SQL so we can render it out into the compiled files #}
  {{ return("/* Import CSV into SAS Server */") }}
{% endmacro %}
