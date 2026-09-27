{#
  Por defecto dbt concatena: dataset del perfil + nombre del esquema del modelo,
  y saldrian datasets como `staging_marts`. Aqui los datasets los crea Terraform
  con nombre fijo -raw, staging, marts, control-, asi que el esquema declarado en
  el modelo se usa tal cual.

  Se conserva la concatenacion cuando el objetivo NO es produccion, para que dos
  personas trabajando a la vez no se pisen las tablas.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}

    {%- if custom_schema_name is none -%}
        {{ default_schema }}

    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}

    {%- else -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}

    {%- endif -%}
{%- endmacro %}
