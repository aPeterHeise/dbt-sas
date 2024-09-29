%if %sysfunc(exist({{ libname }}.{{ new_name }}, DATA)) %then %do;
proc datasets library={{ libname }} memtype=data;
   delete {{ new_name }};
run;
%end;

%if %sysfunc(exist({{ libname }}.{{ new_name }}, VIEW)) %then %do;
proc datasets library={{ libname }} memtype=view;
   delete {{ new_name }};
run;
%end;

%if %sysfunc(exist({{ libname }}.{{ old_name }}, DATA)) %then %do;
proc datasets library={{ libname }} memtype=data;
    change {{ old_name }}={{ new_name }};
run;
%end;

%if %sysfunc(exist({{ libname }}.{{ old_name }}, VIEW)) %then %do;
proc datasets library={{ libname }} memtype=view;
    change {{ old_name }}={{ new_name }};
run;
%end;
