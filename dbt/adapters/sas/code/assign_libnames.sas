/* Auto assign libnames for all the subdirs in a given dir */
%macro assign_libnames(dir);
  %local filrf rc did memcnt name i;
  %let rc = %sysfunc(filename(filrf, &dir));
  %let did = %sysfunc(dopen(&filrf));
  %if &did eq 0 %then %do;
    %put Directory &dir cannot be open or does not exist;
    %return;
  %end;
   %do i = 1 %to %sysfunc(dnum(&did));
   %let name = %qsysfunc(dread(&did,&i));
      %if %qscan(&name, 2, .) = %then %do;
		%put Directory &dir&SEPARATOR&name;
		libname &name base "&dir&SEPARATOR&name";
      %end;
   %end;
   %let rc = %sysfunc(dclose(&did));
   %let rc = %sysfunc(filename(filrf));
%mend assign_libnames;

%assign_libnames({{ path }})
