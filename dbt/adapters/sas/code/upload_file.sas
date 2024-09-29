filename upload "{{ remote_filename }}" encoding="utf-8";
data _null_;
file upload;
input;
put _infile_;
datalines4;
{{ data }}
;;;;
run;
filename upload;
