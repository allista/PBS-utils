Utility scripts to run arbitrary bioinformatics software on a PBS server.
Currently only serial jobs (i.e. jobs that run on a single node exclusively) 
are supported. Several _run scripts are provided: garli_run for GARLI (OpenMP 
version), mb_run for MrBayes (MPI version) and degen_primer_run for [DegenPrimer](https://github.com/allista/DegenPrimer).

Note: for these scripts to work it is necessary that all PBS computing nodes are 
configured to create per-job temporary directory and export it's path as TMPDIR 
environment variable.
