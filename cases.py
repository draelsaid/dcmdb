#!/usr/bin/env python3

from datetime import datetime
import os
import sys
import yaml
import json
import re
import subprocess

class Cases:

    def __init__(self,names=None,path=None,printlev=None,host=None,selection=None):

        self.path = path if path is not None else 'cases'
        self.printlev = printlev if printlev is not None else 1
        self.host = host if host is not None else self.get_hostname()
        self.selection = selection if selection is not None else {}

        if isinstance(self.selection,list):
            self.selection = {k:[] for k in self.selection}

        if names is None:
         if self.selection is not None:
           self.names = list(self.selection.keys())
         else:
           self.names = []
        elif isinstance(names,str):
          self.names = [names]
        else:
          self.names = names

        self.cases,self.names = self.load_cases()

        if len(self.names) == 0:
            print("No cases found")
            print("Available cases:",[x.split('/')[0] for x in find_files(self.path,'meta.yaml')])
            sys.exit()

#########################################################################
    def get_hostname(self):

        import socket

        host = socket.gethostname()
        if re.search(r'^a(a|b|c|d)',host):
            return 'atos'

        return None
#########################################################################
    def scan(self):
      if isinstance(self.cases,dict):
        for case in self.cases:
          self.cases[case].scan()
      else:
          self.cases.scan()

#########################################################################
    def load_cases(self):

        def intersection(lst1, lst2):
            lst3 = [value for value in lst1 if value in lst2]
            lst4 = [value for value in lst1 if value not in lst3]
            return lst3,lst4
    
        meta_file = 'meta.yaml'
        case_list = [x.split('/')[0] for x in find_files(self.path,meta_file)]
        if self.names is not None:
          if len(self.names) > 0:
            case_list,missing = intersection(self.names,case_list)
            if len(missing) > 0:
                print('\nCould not find cases:',missing,'\n')

        if len(case_list) == 0 :
          return {},[]
    
        res = {}
        for x in case_list :
            p ='{}/{}/{}'.format(self.path,x,meta_file)
            meta = yaml.safe_load(open(p))
            if x in self.selection:
             if len(self.selection[x]) > 0 :
              exp_list,missing = intersection(self.selection[x],meta.keys())
              if len(missing) > 0:
                print('\nCould not find exp:',missing,'\n')
              meta = {k:v for k,v in meta.items() if k in exp_list}

            res[x] = Case(self.host, self.path, self.printlev, meta, x)
    
        if self.printlev > 0:
          print("Loaded:",case_list)
        if len(res) > 1 :
          return res,case_list
        else:
          return res[x],case_list

#########################################################################
    def show(self):

      for case,body in self.cases.items():
          print('\nCase:',case)
          print('   ',body)

#########################################################################
    def print(self,printlev=None):

        if printlev is not None:
            self.printlev = printlev

        if self.printlev < 0:
          print('Cases:',self.names)
          return
    
        if isinstance(self.cases,dict):
         for name,case in self.cases.items():
          print('\nCase:',name)
          case.print(self.printlev)
        else:
          self.cases.print(self.printlev)

    def reconstruct(self,dtg=None,leadtime=None,file_template=None):
    
        res =[]
        if isinstance(self.cases,dict):
         for name,case in self.cases.items():
          res.extend(case.reconstruct(dtg, leadtime, file_template))
        else:
          res.extend(self.cases.reconstruct(dtg, leadtime, file_template))

        return res
#########################################################################
#class Case(Cases):
class Case():

    def __init__(self, host, path, printlev, props, case):

        self.host,self.path,self.printlev = host,path,printlev
        self.case = case
        self.printlev = printlev

        self.data = self.load()
        self.runs = {}
        if len(props) > 1 :
         for exp,val in props.items():
          if host in val:
           if exp not in self.data[host]:
              self.data[host][exp] = {}
           self.runs[exp]= Exp(exp, host, printlev, val, self.data[host][exp])
        else:
         for exp,val in props.items():
          if host in val:
           if exp not in self.data[host]:
              self.data[host][exp] = {}
           self.runs= Exp(exp, host, printlev, val, self.data[host][exp])
        self.names= [x for x in props]
          
    def print(self,printlev=None):
        if printlev is not None:
            self.printlev = printlev

        if self.printlev == 0:
           print(' Runs:',self.names)
           return

        if isinstance(self.runs,dict):
          for run,exp in self.runs.items():
           exp.print(self.printlev)
        else:
           self.runs.print(self.printlev)

    def load(self):
        filename= self.path+'/'+self.case+'/data.yaml'
        if os.path.isfile(filename):
         with open(filename, "r") as infile:
           data = json.load(infile)
           infile.close()
        else:
           data = {}
           data[self.host] = {}
        return data

    def scan(self):
        findings = {}
        if isinstance(self.runs,dict):
          for name,exp in self.runs.items():
            result, signal = exp.scan()
            print(signal)
            if signal:
              self.data[self.host][name] = result
            else:
              print("  no data found for",name)
        else:
            result, signal = self.runs.scan()
            if signal:
              self.data[self.host][self.names[0]] = result
            else:
              print("  no data found for",self.names)

        self.dump() 

    def dump(self):
          filename= self.path+'/'+self.case+'/data.yaml'
          with open(filename,"w") as outfile:
              print('  write to:',filename)
              json.dump(self.data,outfile,indent=1)
              outfile.close()

    def reconstruct(self,dtg=None,leadtime=None,file_template=None):
        res = []
        if isinstance(self.runs,dict):
          for run,exp in self.runs.items():
           res.extend(exp.reconstruct(dtg,leadtime,file_template))
        else:
           res.extend(self.runs.reconstruct(dtg,leadtime,file_template))
        return res
#########################################################################
#class Exp(Case):
class Exp():

    def __init__(self, name, host, printlev, val, data):

        self.name = name
        self.host = host
        self.printlev = printlev
        self.file_templates = val['file_templates']
        self.path_template = val[host]['path_template']
        self.domain = val['domain']
        self.data = data


#########################################################################
    def check_template(self,x):

      known_keys = { '%Y': 4,    # Year
                     '%m': 2,    # Month
                     '%d': 2,    # Day
                     '%H': 2,    # Hour
                     '%M': 2,    # Minute
                     '%LLLL': 4, # Leadtime
                     '%LLL': 3,  # Leadtime
                     '*': 0,     # Wildcard
                   }

      mapped_keys = {}
      replace_keys = {}
      y=x
      for k,v in known_keys.items():
         kk = k
         if '%' in k:
           s=f'(\\d{{{v}}})'
         if '*' in k:
           s=f'(.*)'
           kk='\*'
         if '+' in k:
           s=f'\+'
         
         mm = [m.start() for m in re.finditer(kk,x)]
         y = y.replace(k,s)
         if len(mm) > 0:
             mapped_keys[k]= mm[0]
             replace_keys[k]= s
    
      mk = dict(sorted(mapped_keys.items(), key=lambda item: item[1]))
    
      y = y.replace('+','\+')
    
      return y,mk,replace_keys

#########################################################################
    def reconstruct(self,dtg=None,leadtime=None,file_template=None):

        def matching(files,src):
           res = []
           for f in files:
               for x in src:
                 if f == x :
                  res.append(f)
                 else:
                   m = re.fullmatch(f,x) 
                   if m is not None:
                    res.append(m.group(0))

           return res

        def sub(p,dtgs,leadtime):

           dtg = datetime.strptime(dtgs,'%Y-%m-%d %H:%M:%S')
           if isinstance(leadtime,str):
             l = int(leadtime)/3600
           elif isinstance(leadtime,float):
             l = int(leadtime)/3600
           elif isinstance(leadtime,int):
             l = leadtime/3600
           else:
             sys.exit()

           path = p

           re_map = { '%Y': '{:04d}'.format(dtg.year),
                   '%m': '{:02d}'.format(dtg.month),
                   '%d': '{:02d}'.format(dtg.day),
                   '%H': '{:02d}'.format(dtg.hour),
                   '%M': '{:02d}'.format(dtg.minute),
                   '%S': '{:02d}'.format(dtg.second),
                   '%LLLL': '{:04d}'.format(int(l)),
                   '%LLL': '{:03d}'.format(int(l)),
                 }
           for k,v in re_map.items():
             path = path.replace(k,str(v))
 
           return path

        if file_template is None:
          files = self.file_templates
        else:
          files = [file_template]

        result = []
        for file in matching(files,self.data.keys()):
          if dtg is None or dtg == []:
             dtgs = list(self.data[file].keys())
          else:
           if isinstance(dtg,str):
             dtgs = [dtg]
           else:
             dtgs = dtg

          for ddd in dtgs:
            if ddd in self.data[file]:
             if leadtime is None or leadtime == []:
               leadtimes = self.data[file][ddd]
             else:
               if isinstance(leadtime,list):
                 leadtimes = [x*3600 for x in leadtime]
               else:
                 leadtimes = [3600*leadtime]

             result.extend([sub(self.path_template+file,ddd,l) for l in leadtimes if l in self.data[file][ddd]])

        return result

#########################################################################
    def print(self, printlev=None):
        if printlev is not None:
            self.printlev = printlev
        print('\n ',self.name)
        print('   File templates:',self.file_templates)
        print('   Path template :',self.path_template)
        print('   Domain:',self.domain)
        for fname in self.file_templates:
           if fname in self.data:
            content = self.data[fname]
            dates = [d for d in sorted(content)]
            print('   File:',fname)
            if self.printlev < 2:
              print('    Dates:',dates[0],'-',dates[-1])
              print('    Leadtimes:',int(content[dates[0]][0]/3600),'...',int(content[dates[0]][-1]/3600))
            elif self.printlev < 3:
              for date,leadtimes in sorted(content.items()):
                  print('   ',date,':',int(leadtimes[0]/3600),'...',int(leadtimes[-1]/3600))
            elif self.printlev > 2:
              for date,leadtimes in sorted(content.items()):
                  print('   ',date,':',[int(x/3600) for x in leadtimes])
            if self.printlev > 1:
                example = self.reconstruct(dates[0],content[dates[0]][-1]/3600,fname)
                print('    Example:',example)

#########################################################################
    def scan(self):

      print(" scan:",self.name)
      def subsub(path,subdirs,replace_keys):
        
            def pdir(x,replace_keys):
                y = x 
                for k,v in replace_keys.items():
                    if k in y :
                        y = y.replace(k,v)
                return y
        
            result=[]
            content = ecfs_scan(path)
            for cc in content:
              pp = pdir(subdirs[0],replace_keys)
              mm = [m.start() for m in re.finditer(pp,cc)]
              if len(mm) > 0:
                  if len(subdirs) > 1 :
                   subresult = subsub(path+cc,subdirs[1:],replace_keys)
                  else:
                   subresult = [path+cc]
                  result.extend(subresult)
        
            return result


      print('  Search for files named {} in {}'.format(self.file_templates,self.path_template))
    
      i = self.path_template.find('%')
    
      base_path = self.path_template[:i] if i > -1 else self.path_template
      part_path = self.path_template[i:] if i > -1 else ''
    
      if re.match('^ec',base_path):
                subdirs = self.path_template[i:].split('/')
                if subdirs[-1] == '':
                    subdirs.pop()
                x,mk,replace_keys = self.check_template(part_path)
                dirs = subsub(base_path,subdirs,replace_keys)
                content = [d[i:]+cc for d in dirs for cc in ecfs_scan(d)]
      else:
                content = find_files(base_path)
    
      findings = {}
      signal = True
      for file_template in self.file_templates:
              tmp = {}
              x,mk,replace_keys = self.check_template(os.path.join(part_path,file_template))
              for cc in content:
                 zz = re.findall(r""+x+'$',cc)
                 if len(zz) > 0:
                  dtg,l = self.set_timestamp(mk,zz[0])
                  if dtg not in tmp:
                      tmp[dtg] = []
                  tmp[dtg].append(l)
                    
              for k in tmp:
                 tmp[k].sort()
            
              signal = signal and bool(tmp)
              findings[file_template] = tmp

      return findings,signal

#########################################################################
    def set_timestamp(self,mk,z):
      list_keys = ('%Y','%m','%d','%H','%M','%S')
      res = ['0']*6
    
      for j,l in enumerate(list_keys):
          for i,k in enumerate(mk): 
              if l == k :
                 res[j] = z[i]
      dtg = datetime.strptime(':'.join(res),'%Y:%m:%d:%H:%M:%S')
    
      leadtime = None
      for k in mk:
          if k in ('%LLLL','%LLL'):
                   leadtime = 3600*int(z[-1])
    
      return str(dtg),leadtime             
    
#########################################################################
def ecfs_scan(path):

 cmd = subprocess.Popen(['els',path], stdout=subprocess.PIPE)
 cmd_out, cmd_err = cmd.communicate()

 # Decode and filter output
 res = [line.decode("utf-8") for line in cmd_out.splitlines()]
 return res

#########################################################################
def find_files(path,prefix=''):

  # Scan given path and subdirs and return files matching the pattern
  result = []
  try :
    it = os.scandir(path)
  except :
    it = []
  for entry in it:
      if not entry.name.startswith('.') and entry.is_file():
          if re.search(prefix,entry.name) :
            result.append(entry.name)
      if not entry.name.startswith('.') and entry.is_dir():
          subresult = find_files(os.path.join(path,entry.name),prefix)
          subresult = [entry.name + "/" + e for e in subresult]
          result.extend(subresult)
  return result
