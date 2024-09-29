proc datasets library={{ libname }};
{% if dataset is string -%}
    delete {{ dataset }};
{%- else %}
  {% for name in dataset -%}
    delete {{ name }};
  {% endfor -%}
{%- endif %}
run;
