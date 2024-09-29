proc sql;
create view {{ temp_table }} as
{{ sql }};
quit;

filename file1 '{{ temp_filename }}';
proc json nofmtcharacter nosastags out=file1;
export {{ temp_table }};
run;

proc sql;
drop view {{ temp_table }};
quit;
