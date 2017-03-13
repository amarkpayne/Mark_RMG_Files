import os
from time import sleep
from itertools import cycle
from QInput import *


def MakeBashScript(sname,node,wd):
    scriptText='#! /bin/bash \n \n#$ -N '
    scriptText+=sname+'\n#$ -l long\n#$ -l h_rt=120:00:00\n#$ -m ae\n'
    scriptText+='#$ -pe singlenode 8\n#$ -l harpertown\n#$ -q *@node'
    scriptText+=str(node)+'\n#$ -wd '+wd+'\n\nmkdir -p /scratch/ampayne\n'
    scriptText+='g03 ../Files/'+sname+'.com 1>../Logs/sge'+sname
    scriptText+='.log 2>../Logs/sge'+sname+'.error'
    return scriptText

def MakeGaussianFiles(sname,jobType,RString,GS):
    GFtext='%chk='+sname+'.chk\n'
    if jobType==0: #Energy
        GFtext+='# cbs-qb3\n\n'+sname+' Energy\n\n'+GS+'\n'
    if jobType==1: #Frequency
        GFtext+='# b3lyp/cbsb7 iop(7/33=1) freq\n\n'+sname+' freq\n\n'+GS+'\n'
    if jobType==2: #rotor
        GFtext+='# opt=(addred) b3lyp/6-311G(d,p) nosymm\n\n'+sname+' rotor\n'
        GFtext+='\n'+GS+'\n'+RString+'\n'
    return GFtext

def GaussDone(i):
    if i==0:    #Energy File
        with open('Files/'+name+'.log','r') as Lfile:
            Ltext=Lfile.readlines()
            if 'Normal termination of Gaussian' in Ltext[-1]:
                return True

    if i==1:    #Frequency Files
        with open('Files/'+name+'_freq.log','r') as Lfile:
            Ltext=Lfile.readlines()
            if 'Normal termination of Gaussian' in Ltext[-1]:
                return True

    if i==2:    #Rotor Files
        with open('Files/'+name+'_rotor.log','r') as Lfile:
            Ltext=Lfile.readlines()
            if 'Normal termination of Gaussian' in Ltext[-1]:
                return True

def SpaceAtEnd(text):
    if text[-1]=='\n':
        return True
    else:
        return False

def MakeCanthermInput(name):
    Cantext='#!/usr/bin/env python\n# encoding: utf-8\n\n'
    Cantext+='modelChemistry = "CBS-QB3"\nfrequencyScaleFactor = 0.99\n'
    Cantext+='useHinderedRotors = True\nuseBondCorrections = True\n\n'
    Cantext+='species("'+name+'","'+name+'.py")\n\nstatmech("'+name+'")\n'
    Cantext+='thermo("'+name+'", "NASA")'
    return Cantext

def MakeCanthermSpecies(name):
    Speciestext='#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n\n'
    Speciestext+='atoms = '+str(atoms)+'\nbonds = '+str(bonds)+'\nlinear = '
    Speciestext+=str(linear)+'\n'
    Speciestext+='externalSymmetry = '+str(externalSymmetry)+'\n'
    Speciestext+='spinMultiplicity = '+str(spinMultiplicity)+'\n'
    Speciestext+='opticalIsomers = '+str(opticalIsomers)+'\n'
    Speciestext+='energy = {"CBS-QB3": GaussianLog("'+name+'.log")}\n'
    Speciestext+='geometry = GaussianLog("'+name+'.log")\n'
    Speciestext+='frequencies = GaussianLog("'+name+'_freq.log")\n'
    Speciestext+='rotors = [ HinderedRotor(scanLog=GaussianLog("'+name
    Speciestext+='_rotor.log"), pivots='+str(pivots)+',top='+str(top)
    Speciestext+=',symmetry='+str(bondSymmetry)+'),]'
    return Speciestext

def main():
    nodeIndx = cycle(range(len(FreeNodes)))
    cwd=os.getcwd()
    wd=os.path.join(cwd,'Misc')
    RunCantherm=False   # Initialize


    with open(GaussFile,'r') as GFile:
        GaussStructure=GFile.read()
        while SpaceAtEnd(GaussStructure):
            GaussStructure=GaussStructure[:-1]
        GaussStructure+='\n'

    if os.path.exists('Files/')!=True:
        os.mkdir('Files')

    if os.path.exists('Misc/')!=True:
        os.mkdir('Misc')

    if os.path.exists('Logs/')!=True:
        os.mkdir('Logs')

    with open('Files/Efile.sh','w') as Efile:
        Efile.write(MakeBashScript(name,FreeNodes[nodeIndx.next()],wd))

    with open('Files/Ffile.sh','w') as Ffile:
        Ffile.write(MakeBashScript(name+'_freq',FreeNodes[nodeIndx.next()],wd))

    with open('Files/Rfile.sh','w') as Rfile:
        Rfile.write(MakeBashScript(name+'_rotor',FreeNodes[nodeIndx.next()],wd))

    with open('Files/'+name+'.com','w') as Ecom:
        Ecom.write(MakeGaussianFiles(name,0,RString,GaussStructure))

    with open('Files/'+name+'_freq.com','w') as Fcom:
        Fcom.write(MakeGaussianFiles(name+'_freq',1,RString,GaussStructure))

    with open('Files/'+name+'_rotor.com','w') as Rcom:
        Rcom.write(MakeGaussianFiles(name+'_rotor',2,RString,GaussStructure))

    with open('Files/input.py','w') as Ifile:
        Ifile.write(MakeCanthermInput(name))

    with open('Files/'+name+'.py','w') as Sfile:
        Sfile.write(MakeCanthermSpecies(name))


    # Submit the Job Scripts to SGE
    os.system('qsub Files/Efile.sh')
    os.system('qsub Files/Ffile.sh')
    os.system('qsub Files/Rfile.sh')

    for t in range(0,MaxTime):     # Check to see if Gauss Jobs are Done
        sleep(60)
        if all(GaussDone(i) for i in range(3)):
            RunCantherm=True
            break

    if RunCantherm:
        Canthermlog=' 1>Logs/Cantherm.log'
        Canthermerror=' 2>Logs/Cantherm.error'
        Cantherminput=' Files/input.py'
        runCommand='python $CANTHERM'+Cantherminput+Canthermlog+Canthermerror
        os.system(runCommand)

    print 'Cantherm Job Successfully Submitted'


if __name__ == '__main__':
    main()
