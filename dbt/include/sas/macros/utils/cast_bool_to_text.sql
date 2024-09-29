{% macro default__cast_bool_to_text(field) %}
    case when {{ field }} then 'true' else 'false' end
{% endmacro %}
