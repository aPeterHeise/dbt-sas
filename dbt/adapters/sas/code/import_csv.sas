proc import datafile="{{ filename }}"
    out={{ libname }}.{{ dataset }}
    dbms=csv
    replace;
    getnames=yes;
run;
