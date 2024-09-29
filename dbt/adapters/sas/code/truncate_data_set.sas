proc sql;
    delete from {{ libname }}.{{ dataset }};
quit;
