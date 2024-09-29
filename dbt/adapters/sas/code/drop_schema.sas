%macro delete_file(path);
  %local filrf rc;
  %let rc = %sysfunc(filename(filrf, &path));
  %if &rc eq 0 and %sysfunc(fexist(&filrf)) %then %do;
    %put Deleting file &path;
    %let rc = %sysfunc(fdelete(&filrf));
  %end;
  %let rc = %sysfunc(filename(fname));
%mend delete_file;

%macro delete_dir_content(dir);
  %local filrf rc did memcnt name i fullname;
  %let rc = %sysfunc(filename(filrf, &dir));
  %let did = %sysfunc(dopen(&filrf));
  %if &did eq 0 %then %do;
    %put Directory &dir cannot be open or does not exist;
    %return;
  %end;
  %do i = 1 %to %sysfunc(dnum(&did));
  %let name = %qsysfunc(dread(&did,&i));
    %let fullname = &dir&SEPARATOR&name;
    %delete_file(&fullname)
  %end;
  %let rc = %sysfunc(dclose(&did));
  %let rc = %sysfunc(filename(filrf));
%mend delete_dir_content;

/* Deletes all datasets */
proc datasets lib={{ libname }} kill;
run;

/* Delete dir content */
%delete_dir_content({{ path }})

quit;
ods path reset;

libname {{ libname }} clear;
