# The DE_330 case meta database 

## Introduction

`dcmbd` is an attempt to bring some order in the output from the case stuides performed within DE_330. The initial cases will be done with different setup using different name conventions and the idea is to handle these differences in an organized manner. The meta database consists of metadata for individual cases along with data availibility information. The aim is to allow an easy access to data without having to worry to much about the location. 

## The metadata

For each case we suggest to create a directory under `cases`. Pick a name that is descriptive and unique enough. In a file called meta.yaml we introduce

``` yaml
mcp43h2_prod: 

  file_templates : ['fc%Y%m%d%H+%LLLgrib_sfxs','fc%Y%m%d%H+%LLLgrib2_fp']

  atos:
     path_template : 'ec:/snh/harmonie/mcp43h2_prod/%Y/%m/%d/%H/mbr000/'

  domain : 
     name : 'METCOOP25D'
     resolution : 2500
     levels : 65
```

where 
 * the top level is the experiment name or similar
 * `file_templates` describes the files of interest. Note that date/time information is parameterized using standard linux/python notation.
 * `atos` here tells us where the data is located. For the future we could consider lumi and other hosts as well
 * `path_template` the search path for the data, note that ECFS notation is supported.
 * `domain` gives some information about the domain used. Could contain geometry information as well.

In each `meta.yaml` file we may specify an arbitrary number of experiments/runs.

## The python support

A module and a command line tool has been created to support inspection of the case content and recounstruction of file paths. The yaml files of course could be accessed from other languages such as R or julia as well.

### Command line tool

Running `./chase.py` will show some options. Assuming we're running on atos list cases and their content is done by 
```
./chase.py -list 
```
where more options can be added. Add a few `-v` or `-s` to see more/less information.

### Generate the data availability information

For a newly added case the data part has to be benerated running
```
./chase.py -scan -case MYCASE [ -exp MYEXP ]
```
This will generate the file `cases/MYCASE/data.yaml` containing all dates and leadtimes (in seconds) for the given files. Default is to scan all experimetns within a case, give MYEXP to just updated a single run. Note that scanning ECFS may take some minutes. Don't forget to commit the new file to the repo after you've created or updated it. For now commits should be done directly to the master branch.

### The cases module

The file `cases.py` contains some methods to access information and reconstruct file names. Check `examples.py` for how to use it.

## Caveats

This is still work in progess and the usefulness still to be proven. At the moment leadtimes in subhourly format is not yet handled.

