import os
import subprocess
import glob
import ROOT
import array
import ROOT.TObject
from optparse import OptionParser
from termcolor import colored

def get_options():
    parser = OptionParser()
    parser.add_option("--inputWSFile", dest="inputWSFile", default=None, help="Input RooWorkspace file. If loading snapshot then use a post-fit workspace where the option --saveWorkspace was set")
    parser.add_option("--loadSnapshot", dest="loadSnapshot", default=None, help="Load best-fit snapshot name")
    parser.add_option("--ext", dest="ext", default='', help="Extension for saving")
    parser.add_option("--nToys", dest="nToys", default=500, type='int', help="Number of toys")
    parser.add_option("--POIs", dest="POIs", default="r", help="Parameters of interest in fit")
    parser.add_option("--maxExpectSignal", dest="maxExpectSignal", type='int', default=1, help="highest expectSignal parameter to generate toys for bias test")
    parser.add_option("--batch", dest="batch", default="", help="Batch system [condor]") #default="condor"
    parser.add_option("--queue", dest="queue", default="workday", help="Change condor queue")
    parser.add_option('--dryRun',dest='dryRun', default=False, action="store_true", help='Dry run')
    parser.add_option('--scaleDC',dest='scaleDC', default=True, action="store_true", help='Scale the signal of datacard by some factor')
    parser.add_option('--scaleDCfactor',dest='scaleDCfactor', default=0.001, type='float', help='Scale the signal of datacard by some factor')
    return parser.parse_args()

def search_and_use_file(directory, filename):
    if os.path.exists(directory):
        for root, dirs, files in os.walk(directory):
            if filename in files:
                file_path = os.path.join(root, filename)  # Get the full path of the file
                return file_path  # Exit the function if the file is found
    else:
        return None

def run_command(command_):
     os.system("cmsenv")
     os.system(command_)

def edit_file(file_name, str_to_modify):
    with open(file_name, "r") as file:
         lines = file.readlines()

    for i in range(len(lines)):
         lines[i] = lines[i].replace(str_to_modify, "")

    with open(file_name, "w") as file:
         file.writelines(lines)
    
def remove_syst(file_name):
    with open(file_name, "r") as file:
         lines = file.readlines()

    keyword = "kmax"
    new_line = "kmax *\n"	    
    
    for i in range(len(lines)):
        if keyword in lines[i]:
            lines[i] = new_line    
 
    filtered_lines = [line for line in lines if " shape " not in line and " lnN " not in line and " gmN " not in line]
    parts = file_name.split('.')
    if len(parts) == 2:
		new_file_name = parts[0] + "_StatOnly." + parts[1]
    if len(parts) == 3:
        new_file_name = parts[0] +"."+ parts[1] + "_StatOnly." + parts[2]
    with open(new_file_name, "w") as file:
         file.writelines(filtered_lines)

class DatacardModifier(object):
    def __init__(self, opt):
        self.scaleDC = opt.scaleDC
        self.scaleDCfactor = opt.scaleDCfactor

    def getRateList(self, datacard_name):
      '''
        Get the list of the signal and background rates from the initial datacard
      '''
      proc_lines = []
      rate_line = ''
      f = open(datacard_name)
      lines = f.readlines()
      for line in lines:
          if line.startswith('rate'):
              rate_line = line
          if line.startswith('process'):
              proc_lines.append(line.strip())
      
      rate_list = []
      proc_list = []
      word_to_remove = "rate"
      rates = rate_line.split()
      for rate in rates: 
          if rate != word_to_remove:
              rate_list.append(float(rate))

      word_to_remove = "process"
      proc_ids = proc_lines[1].split()
      for proc_id in proc_ids: 
          if proc_id != word_to_remove:
              proc_list.append(float(proc_id))

      if len(rate_list) == len(proc_list):
          print "Initial rate list"
          print rate_list
#          print proc_list
          return rate_list, proc_list
      else: 
          print ("[ERROR]The length of the rate and process array didn't match")

    def updateRateList(self, rate_list, proc_list):
      '''
        Update the signal rates according to given coupling scenario
      '''
      updated_rate_list = []
      for rate, proc in zip(rate_list, proc_list):
          if proc < 1:
             print ("  %f  "%rate)
             updated_rate = rate * self.scaleDCfactor
          else:
             updated_rate = rate
          updated_rate_list.append(updated_rate)
      print "Updated signal scaled rate list"
      print updated_rate_list 
      return updated_rate_list
  
    def updateDatacard(self, datacard_name, updated_rate_list):
      '''
        Update the datacard with the updated signal rates
      '''
      updated_datacard_name = datacard_name + '_tmp'
      updated_datacard = open(updated_datacard_name, 'w+')
      datacard = open(datacard_name)
      lines = datacard.readlines()
      for line in lines:
        if 'rate ' in line:
          rate_line = 'rate                                                           '            
          for updated_rate in updated_rate_list:
            rate_line += '{}  '.format(updated_rate)    
          updated_datacard.write(rate_line + '\n')
  
        else:
          updated_datacard.write(line)
  
      updated_datacard.close()
 
      os.system('cp {} {}'.format(datacard_name, datacard_name + "_backup"))
      print 'mv {} {}'.format(updated_datacard_name, datacard_name)
      os.system('mv {} {}'.format(updated_datacard_name, datacard_name))
  
    def process(self, datacard_name):
      if self.scaleDC:
#        rate_list = self.getRateList(datacard_name=datacard_name)
        rate_list, proc_list = self.getRateList(datacard_name=datacard_name)
        updated_rate_list = self.updateRateList(rate_list=rate_list, proc_list=proc_list)
        self.updateDatacard(datacard_name=datacard_name, updated_rate_list=updated_rate_list)
  
if __name__ == "__main__":
  (opt,args) = get_options()
  # Create jobs directory
#  masses=[1,2,3,4,5,6,7,8,10,12,14,16,18,20] #use integers to not mess up with file names with "." or "p"
  masses=[2] #use integers to not mess up with file names with "." or "p"
#  ctaus=["0.00001","0.00010","0.00100","0.01000","0.10000","1","10","100","1000",10000]
#  ctaus=["0.00001","0.00010","0.00100","0.01000","0.10000"]
  ctaus=["10"]

  for mass in masses:
      for ctau in ctaus:
          if not os.path.isdir("./Models_mHNL%i_ctau_%s/"%(mass, ctau)): os.system("mkdir ./Models_mHNL%i_ctau_%s/"%(mass, ctau))
          if not os.path.isdir("./Models_mHNL%i_ctau_%s/jobs"%(mass, ctau)): os.system("mkdir ./Models_mHNL%i_ctau_%s/jobs"%(mass, ctau))
#          if not os.path.isdir("./Models_%s/toys/jobs"%(opt.ext)): os.system("mkdir ./Models_%s/toys/jobs"%(opt.ext))
          if float(ctau) >= 1:
              print (ctau)
#              directories = ['../datacards/EXO-20-009/AllPoints_OldSystematics/DIRAC_cards_ctau_new/','EXO-21-013/cards/combined/coupling_12/HNL_dirac_all_ctau%s_massHNL%ip0/'%(ctau,mass), '../datacards/EXO-22-017/muon/','../datacards/EXO-22-019/23_06_05/']
#              filenames = ['HNL_muonDiracType_mHNL%ip0_pl%s.00000_comb.txt'%(mass,ctau),'modified_out_combined.txt','HNL_muonDiracType_mHNL%ip0_pl%s_comb.txt'%(mass,ctau), 'HNL_muonType_mHNL_%ip0_ctau_%sp0_comb.txt'%(mass,ctau)]
#              directories = ['../datacards/EXO-20-009/AllPoints_OldSystematics/DIRAC_cards_ctau_new/','../datacards/EXO-22-017/muon/','../datacards/EXO-22-019/23_06_05/']
#              filenames = ['HNL_muonDiracType_mHNL%ip0_pl%s.00000_comb.txt'%(mass,ctau),'HNL_muonDiracType_mHNL%ip0_pl%s_comb.txt'%(mass,ctau),'HNL_muonType_mHNL_%ip0_ctau_%sp0_comb.txt'%(mass,ctau)]
#              directories = ['../datacards/EXO-20-009/AllPoints_OldSystematics/DIRAC_cards_ctau_new/']
#              filenames = ['HNL_muonDiracType_mHNL%ip0_pl%s.00000_comb.txt'%(mass,ctau)]
#              directories = ['../datacards/EXO-22-017/muon/','../datacards/EXO-22-019/23_06_05/']
#              filenames = ['HNL_muonDiracType_mHNL%ip0_pl%s_comb.txt'%(mass,ctau), 'HNL_muonType_mHNL_%ip0_ctau_%sp0_comb.txt'%(mass,ctau)]
              directories = ['../datacards/EXO-22-019/23_06_05/']
              filenames = ['HNL_muonType_mHNL_%ip0_ctau_%sp0_comb.txt'%(mass,ctau)]
              str_to_modify_ = 'cards/combined/coupling_12/HNL_dirac_all_ctau%s_massHNL%ip0/'%(ctau,mass)
          if float(ctau) < 1:
              print (ctau)
              #ctau_str = str(ctau)
              ctau_parts = ctau.split(".")
#              directories = ['../datacards/EXO-20-009/AllPoints_OldSystematics/DIRAC_cards_ctau_new/','EXO-21-013/cards/combined/coupling_12/HNL_dirac_all_ctau0p%s_massHNL%ip0/'%(ctau_parts[1],mass), '../datacards/EXO-22-017/muon/','../datacards/EXO-22-019/23_06_05/']
#              filenames = ['HNL_muonDiracType_mHNL%ip0_pl0.%s_comb.txt'%(mass, ctau_parts[1]),'modified_out_combined.txt','HNL_muonDiracType_mHNL%ip0_pl0p%s_comb.txt'%(mass, ctau_parts[1]), 'HNL_muonType_mHNL_%ip0_ctau_0p%s_comb.txt'%(mass, ctau_parts[1])]
#              directories = ['../datacards/EXO-20-009/AllPoints_OldSystematics/DIRAC_cards_ctau_new/','../datacards/EXO-22-017/muon/','../datacards/EXO-22-019/23_06_05/']
#              filenames = ['HNL_muonDiracType_mHNL%ip0_pl0.%s_comb.txt'%(mass, ctau_parts[1]),'HNL_muonDiracType_mHNL%ip0_pl0p%s_comb.txt'%(mass, ctau_parts[1]), 'HNL_muonType_mHNL_%ip0_ctau_0p%s_comb.txt'%(mass, ctau_parts[1])]
#              directories = ['../datacards/EXO-20-009/AllPoints_OldSystematics/DIRAC_cards_ctau_new/']
#              filenames = ['HNL_muonDiracType_mHNL%ip0_pl0.%s_comb.txt'%(mass, ctau_parts[1])]
#              directories = ['../datacards/EXO-22-017/muon/','../datacards/EXO-22-019/23_06_05/']
#              filenames = ['HNL_muonDiracType_mHNL%ip0_pl0p%s_comb.txt'%(mass, ctau_parts[1]), 'HNL_muonType_mHNL_%ip0_ctau_0p%s_comb.txt'%(mass, ctau_parts[1])]
              directories = ['../datacards/EXO-22-019/23_06_05/']
              filenames = ['HNL_muonType_mHNL_%ip0_ctau_0p%s_comb.txt'%(mass, ctau_parts[1])]
              str_to_modify_ = 'cards/combined/coupling_12/HNL_dirac_all_ctau0p%s_massHNL%ip0/'%(ctau_parts[1],mass)
#          names = ['EXO-20-009','EXO-21-013','EXO-22-017','EXO-22-019']
#          names = ['EXO-20-009','EXO-22-017','EXO-22-019']
#          names = ['EXO-22-017','EXO-22-019']
          names = ['EXO-22-019']
#          names = ['EXO-20-009']
          all_valid_files = ""
          valid_point = False
          for directory, filename, name in zip(directories, filenames, names):
              #print(directory, filename)
              file_path_ = search_and_use_file(directory, filename) 
              if file_path_ is not None:
                  all_valid_files += ' ' + name + '=' + file_path_
          comb_datacard_name = "HNL_datacard_mHNL%i_ctau_%s_combined.txt"%(mass, ctau)
          if all_valid_files is not '':	
              valid_point = True
              print (colored("#merging datacard for mass=%i and ctau=%s"%(mass, ctau),'green'))
              print ("combineCards.py\t" + all_valid_files + "  > HNL_datacard_mHNL%i_ctau_%s_combined.txt"%(mass, ctau))
              command = "combineCards.py\t" + all_valid_files + "  > HNL_datacard_mHNL%i_ctau_%s_combined.txt"%(mass, ctau)
#combine cards
              run_command(command)
#If any modification required in the combined .txt file
              edit_file(comb_datacard_name, str_to_modify_)
#To remove lnN, shape and gmN Syst. from the datacard
              remove_syst(comb_datacard_name)
              parts = comb_datacard_name.split('.')
#              os.system("text2workspace.py " + parts[0] +"_StatOnly." + parts[1])
              txtToWS_cmd = "text2workspace.py " + "HNL_datacard_mHNL%i_ctau_%s_combined.txt"%(mass, ctau)
              limit_cmd = "combine HNL_datacard_mHNL%i_ctau_%s_combined.root -M AsymptoticLimits --redefineSignalPOIs r --trackParameters r --setParameters norm=1 --freezeParameter norm --saveWorkspace --cminDefaultMinimizerStrategy 0 --X-rtd MINIMIZER_freezeDisassociatedParams --X-rtd MINIMIZER_multiMin_hideConstants --X-rtd MINIMIZER_multiMin_maskConstraints --X-rtd MINIMIZER_multiMin_maskChannels=2 -n mHNL_%i_ctau-%s"%(mass, ctau, mass, ctau)
              if opt.dryRun:
                   print (limit_cmd)
                   os.system(txtToWS_cmd)
                   os.system(limit_cmd)
                   filename = "./higgsCombinemHNL_%i_ctau-%s.AsymptoticLimits.mH120.root"%(mass, ctau)
                   if os.path.exists(filename):
                     file = ROOT.TFile.Open(filename, "READ")
                     if file and not file.IsZombie(): 
                       file = ROOT.TFile.Open(filename, "READ")
                       tree = file.Get("limit")
                       if tree and tree.GetEntries() < 3 and opt.scaleDC: 
                            file.Close()
                            DatacardModifier(opt=opt).process(comb_datacard_name)
                            os.system(txtToWS_cmd)
                            os.system(limit_cmd)
#                            filename = "./higgsCombinemHNL_%i_ctau-%s.AsymptoticLimits.mH120.root"%(mass, ctau)
                            if os.path.exists(filename):
                                file = ROOT.TFile.Open(filename, "UPDATE")
                                tree = file.Get("limit")
                                branch = tree.GetBranch("limit")
                                leaf_value = array.array('d', [0])
                                branch.SetAddress(leaf_value)
                                i=0
                                #for event in tree:
                                for event in range(tree.GetEntries()):
                                    branch.GetEntry(event)
                                    leaf_value[0] *= (1.0 / opt.scaleDCfactor)
                                    tree.Fill()
                                file.Write("", ROOT.TObject.kOverwrite)
                                file.Close()    
#                       if not tree:
#                            os.system("rm -rf %s"%filename)    
              if opt.batch == 'condor' and valid_point:
                   if not os.path.isdir("./Models_mHNL%i_ctau_%s"%(mass, ctau)): os.system("mkdir ./Models_mHNL%i_ctau_%s"%(mass, ctau))
                   if not os.path.isdir("./Models_mHNL%i_ctau_%s/jobs"%(mass, ctau)): os.system("mkdir ./Models_mHNL%i_ctau_%s/jobs"%(mass, ctau))

                   # Delete all old jobs
                   for job in glob.glob("./Models_mHNL%i_ctau_%s/jobs/sub*.sh"%(mass, ctau)): os.system("rm %s"%job)

                   fsub = open("./Models_mHNL%i_ctau_%s/jobs/sub_limits.sh"%(mass, ctau),'w')
                   fsub.write("#!/bin/bash\n")
                   fsub.write("ulimit -s unlimited\n")
                   fsub.write("set -e\n")
                   fsub.write("cd %s/src/combine_HNL/datacards/Models_mHNL%i_ctau_%s/\n"%(os.environ['CMSSW_BASE'], mass, ctau))
                   fsub.write("source /cvmfs/cms.cern.ch/cmsset_default.sh\n")
                   fsub.write("eval `scramv1 runtime -sh`\n\n")
  #                fsub.write("ExpSig=$1\n\n")

                   # Combine command
                   fsub.write("#Combine command\n")              
                   fsub.write(txtToWS_cmd + "\n")
                   fsub.write(limit_cmd)
                   fsub.close()

                   fcondor = open("./Models_mHNL%i_ctau_%s/jobs/sub_limits.sub"%(mass, ctau),'w')
              #    fcondor.write("\n")
                   fcondor.write("universe = vanilla\n")
                   fcondor.write("Executable = sub_limits.sh\n")
   #               fcondor.write("Arguments = %s\n"%ExpSig)
                   fcondor.write("output                = %s/src/flashggFinalFit/Combine/Models_mHNL%i_ctau_%s/toys/jobs/sub_limits.$(ClusterId).$(ProcId).out\n"%(os.environ['CMSSW_BASE'], mass, ctau))
                   fcondor.write("error                 = %s/src/flashggFinalFit/Combine/Models_mHNL%i_ctau_%s/toys/jobs/sub_limits.$(ClusterId).$(ProcId).err\n"%(os.environ['CMSSW_BASE'], mass, ctau))
                   fcondor.write("log                   = %s/src/flashggFinalFit/Combine/Models_mHNL%i_ctau_%s/toys/jobs/sub_limits.$(ClusterId).log\n\n"%(os.environ['CMSSW_BASE'], mass, ctau))
                   fcondor.write("on_exit_hold = (ExitBySignal == True) || (ExitCode != 0)\n")
                   fcondor.write("periodic_release =  (NumJobStarts < 3) && ((CurrentTime - EnteredCurrentStatus) > 600)\n\n")
                   fcondor.write("+JobFlavour = \"%s\"\n"%(opt.queue))
                   fcondor.write("Queue\n\n")
                   fcondor.close()
                   # Submission
                   os.system("chmod 775 ./Models_mHNL%i_ctau_%s/jobs/sub_toys.sh"%(mass, ctau))
                   print "Submitting condor_submit for mHNL = %i and ctau = %s"%(mass, ctau)
#                  if not opt.dryRun: os.system("cd ./Models_mHNL%i_ctau_%s/toys/jobs; source /cvmfs/cms.cern.ch/cmsset_default.sh; eval `scramv1 runtime -sh`; condor_submit sub_toys.sub; cd ../../.."%(mass, ctau))
 
