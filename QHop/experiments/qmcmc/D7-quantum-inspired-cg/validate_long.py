import sys; sys.path.insert(0,'/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D7-quantum-inspired-cg')
import numpy as np, cg, qmc
inst=cg.Inst("sk",8,11); beta=2/np.sqrt(8)
E=qmc.ising_energies(inst.J,inst.h); pi=np.exp(-beta*(E-E.min())); pi/=pi.sum(); print("exact",pi@E)
for m,k,g in [("dec",3,"block"),("q",4,"subset"),("q",4,"cluster")]:
    r=cg.chain(inst,m,beta,tlimit=40,seed=9,k=k,gmode=g,moves_per_rec=1)
    x=r["E"][2000:]; tau=qmc.iat(x); se=x.std()*np.sqrt(tau/len(x))
    print(m,k,g,len(x),x.mean(),"se",se,"tau",tau,"z",(x.mean()-pi@E)/se)
