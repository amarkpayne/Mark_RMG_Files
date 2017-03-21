import os
from time import sleep
from itertools import cycle
from QInput import *


def make_bash_script(species, node, wd):
    script_text = '#! /bin/bash \n \n#$ -N '
    script_text += species+'\n#$ -l long\n#$ -l h_rt=120:00:00\n#$ -m ae\n'
    script_text += '#$ -pe singlenode 8\n#$ -l harpertown\n#$ -q *@node'
    script_text += str(node)+'\n#$ -wd '+wd+'\n\nmkdir -p /scratch/ampayne\n'
    script_text += 'g03 ../Files/'+species+'.com 1>../Logs/sge'+species
    script_text += '.log 2>../Logs/sge'+species+'.error'
    return script_text


def make_gaussian_file(species, job_type, rotor_string, coordinates):
    file_text = '%chk='+species+'.chk\n'
    if job_type == 0:  # Energy
        file_text += '# cbs-qb3\n\n'+species+' Energy\n\n'+coordinates+'\n'
    if job_type == 1:  # Frequency
        file_text += '# b3lyp/cbsb7 iop(7/33=1) freq\n\n'+species+' freq\n\n'+coordinates+'\n'
    if job_type == 2:  # rotor
        file_text += '# opt=(addred) b3lyp/6-311G(d,p) nosymm\n\n'+species+' rotor\n'
        file_text += '\n'+coordinates+'\n'+rotor_string+'\n'
    return file_text


def gauss_done(i):
    if i == 0:    # Energy File
        with open('Files/'+name+'.log', 'r') as log_file:
            log_text = log_file.readlines()
            if 'Normal termination of Gaussian' in log_text[-1]:
                return True

    if i == 1:    # Frequency Files
        with open('Files/'+name+'_freq.log', 'r') as log_file:
            log_text = log_file.readlines()
            if 'Normal termination of Gaussian' in log_text[-1]:
                return True

    else:    # Rotor Files
        with open('Files/'+name+'_rotor'+str((i-1))+'.log', 'r') as log_file:
            log_text = log_file.readlines()
            if 'Normal termination of Gaussian' in log_text[-1]:
                return True


def space_at_end(text):
    if text[-1] == '\n':
        return True
    else:
        return False


def make_cantherm_input(species):
    can_text = '#!/usr/bin/env python\n# encoding: utf-8\n\n'
    can_text += 'modelChemistry = "CBS-QB3"\nfrequencyScaleFactor = 0.99\n'
    can_text += 'useHinderedRotors = True\nuseBondCorrections = True\n\n'
    can_text += 'species("'+species+'","'+species+'.py")\n\nstatmech("'+species+'")\n'
    can_text += 'thermo("'+species+'", "NASA")'
    return can_text


def make_cantherm_species(species):
    species_text = '#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n\n'
    species_text += 'atoms = '+str(atoms)+'\nbonds = '+str(bonds)+'\nlinear = '
    species_text += str(linear)+'\n'
    species_text += 'externalSymmetry = '+str(externalSymmetry)+'\n'
    species_text += 'spinMultiplicity = '+str(spinMultiplicity)+'\n'
    species_text += 'opticalIsomers = '+str(opticalIsomers)+'\n'
    species_text += 'energy = {"CBS-QB3": GaussianLog("'+species+'.log")}\n'
    species_text += 'geometry = GaussianLog("'+species+'.log")\n'
    species_text += 'frequencies = GaussianLog("'+species+'_freq.log")\n'
    species_text += 'rotors = ['
    for i in range(1, len(rotor_string)+1):
        species_text += 'HinderedRotor(scanLog=GaussianLog("'+species
        species_text += '_rotor'+str(i)+'.log"), pivots='+str(pivots[i])
        species_text += ',top='+str(top[i])
        species_text += ',symmetry='+str(bondSymmetry[i])+'),'
    species_text += ']'
    return species_text


def main():
    node_index = cycle(range(len(FreeNodes)))
    cwd = os.getcwd()
    wd = os.path.join(cwd, 'Misc')
    run_cantherm = False   # Initialize

    with open(GaussFile, 'r') as GFile:
        gauss_structure = GFile.read()
        while space_at_end(gauss_structure):
            gauss_structure = gauss_structure[:-1]
        gauss_structure += '\n'

    if not os.path.exists('Files/'):
        os.mkdir('Files')

    if not os.path.exists('Misc/'):
        os.mkdir('Misc')

    if not os.path.exists('Logs/'):
        os.mkdir('Logs')

    with open('Files/Efile.sh', 'w') as Efile:
        Efile.write(make_bash_script(name, FreeNodes[node_index.next()], wd))

    with open('Files/Ffile.sh', 'w') as Ffile:
        Ffile.write(make_bash_script(name+'_freq', FreeNodes[node_index.next()], wd))

    for i in range(1, len(rotor_string)+1):
        with open('Files/Rfile'+str(i)+'.sh', 'w') as Rfile:
            Rfile.write(make_bash_script(name+'_rotor'+str(i), FreeNodes[node_index.next()], wd))

    with open('Files/'+name+'.com', 'w') as Ecom:
        Ecom.write(make_gaussian_file(name, 0, rotor_string, gauss_structure))

    with open('Files/'+name+'_freq.com', 'w') as Fcom:
        Fcom.write(make_gaussian_file(name+'_freq', 1, rotor_string, gauss_structure))

    for i in range(1, len(rotor_string)+1):
        with open('Files/'+name+'_rotor'+str(i)+'.com', 'w') as Rcom:
            Rcom.write(make_gaussian_file(name+'_rotor'+str(i), 2, rotor_string[i-1], gauss_structure))

    with open('Files/input.py', 'w') as Ifile:
        Ifile.write(make_cantherm_input(name))

    with open('Files/'+name+'.py', 'w') as Sfile:
        Sfile.write(make_cantherm_species(name))

    # Submit the Job Scripts to SGE
    os.system('qsub Files/Efile.sh')
    os.system('qsub Files/Ffile.sh')
    for i in range(1, len(rotor_string)+1):
        os.system('qsub Files/Rfile'+str(i)+'.sh')

    for t in range(0, MaxTime):     # Check to see if Gauss Jobs are Done
        sleep(60)
        if all(gauss_done(i) for i in range(0, len(rotor_string)+2)):
            run_cantherm = True
            break

    if run_cantherm:
        cantherm_log = ' 1>Logs/Cantherm.log'
        cantherm_error = ' 2>Logs/Cantherm.error'
        cantherm_input = ' Files/input.py'
        run_command = 'python $CANTHERM'+cantherm_input+cantherm_log+cantherm_error
        os.system(run_command)

    print 'Cantherm Job Successfully Submitted'


if __name__ == '__main__':
    main()
