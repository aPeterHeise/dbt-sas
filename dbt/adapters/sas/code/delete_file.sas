%macro delete_file(path);
  %local filrf rc;
  %let rc = %sysfunc(filename(filrf, &path));
  %if &rc eq 0 and %sysfunc(fexist(&filrf)) %then %do;
    %put Deleting file &path;
    %let rc = %sysfunc(fdelete(&filrf));
  %end;
  %let rc = %sysfunc(filename(fname));
%mend delete_file;

%delete_file({{ remote_filename }})
