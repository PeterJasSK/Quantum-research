import sys, numpy as np
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc
n=10; betas=np.array([0.1,0.2,0.3,0.5,0.7,1.0,1.5,2.0,3.0])
rows=[]
for seed in range(3):
    J,h=qmc.sk_instance(n,100+seed); E=qmc.ising_energies(J,h); g,t=qmc.draw_params(seed,16)
    Qq=qmc.quantum_Q(E,g,t); Ql=qmc.local_Q(n); Qu=qmc.uniform_Q(n)
    # short-time "close" quantum proposal
    g2,t2=qmc.draw_params(seed,16,t=(0.3,1.5)); Qs=qmc.quantum_Q(E,g2,t2)
    C=qmc.thermo(E,n,betas)
    for b,c in zip(betas,C):
        gq,gl,gu,gs=[qmc.gap(Q,E,b) for Q in (Qq,Ql,Qu,Qs)]
        rows.append((seed,b,c,gl,gu,gq,gs))
rows=np.array(rows)
print("beta  C/n   gap_local gap_unif gap_q gap_qshort  q/local q/best(l,u)  qshort/best")
for b in betas:
    r=rows[rows[:,1]==b]; m=np.median(r,0)
    best=np.maximum(r[:,3],r[:,4])
    print(f"{b:4.1f} {m[2]:.3f} {m[3]:.4f} {m[4]:.4f} {m[5]:.4f} {m[6]:.4f}  {np.median(r[:,5]/r[:,3]):6.2f} {np.median(r[:,5]/best):6.2f} {np.median(r[:,6]/best):6.2f}")
