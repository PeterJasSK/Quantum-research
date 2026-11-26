// Micro-benchmark: single-spin Metropolis on dense SK (Gaussian J) and sparse 3-regular graph.
// Reports ns per attempted spin flip (one proposal + accept/reject, incl. RNG).
// Variants: dense-naive (dE computed as O(n) dot product per proposal),
//           dense-field (cached local fields h_i; O(1) dE, O(n) update on accept),
//           sparse-3reg (dE from 3 neighbours).
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <stdint.h>

static uint64_t s[2] = {0x9E3779B97F4A7C15ULL, 0xBF58476D1CE4E5B9ULL};
static inline uint64_t rotl(uint64_t x, int k){return (x<<k)|(x>>(64-k));}
static inline uint64_t next(void){uint64_t s0=s[0],s1=s[1],r=s0+s1;s1^=s0;s[0]=rotl(s0,24)^s1^(s1<<16);s[1]=rotl(s1,37);return r;}
static inline double u01(void){return (next()>>11)*(1.0/9007199254740992.0);}
static double gauss(void){double a=u01()+1e-300,b=u01();return sqrt(-2*log(a))*cos(6.283185307179586*b);}
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+1e-9*t.tv_nsec;}

int main(int argc,char**argv){
  int sizes[]={10,30,100,300,1000,3000};
  double betas[]={0.3,1.0,3.0}; // high T, near T_c (SK T_c=1 in units J/sqrt(n)), low T
  printf("n,beta,variant,ns_per_attempt,acc_rate\n");
  for(int si=0;si<6;si++){
    int n=sizes[si];
    double*J=malloc(sizeof(double)*n*n); int*sp=malloc(sizeof(int)*n); double*h=malloc(sizeof(double)*n);
    for(int i=0;i<n;i++)for(int j=i;j<n;j++){double v=(i==j)?0:gauss()/sqrt(n);J[i*n+j]=v;J[j*n+i]=v;}
    // sparse 3-regular-ish: ring + random matching (degree 3), J=+-1
    int*nb=malloc(sizeof(int)*3*n); double*Js=malloc(sizeof(double)*3*n);
    int*perm=malloc(sizeof(int)*n); for(int i=0;i<n;i++)perm[i]=i;
    for(int i=n-1;i>0;i--){int k=next()%(i+1);int t=perm[i];perm[i]=perm[k];perm[k]=t;}
    int*mate=malloc(sizeof(int)*n); for(int i=0;i<n;i+=2){int a=perm[i],b=perm[(i+1)%n];mate[a]=b;mate[b]=a;}
    for(int i=0;i<n;i++){nb[3*i]=(i+1)%n;nb[3*i+1]=(i+n-1)%n;nb[3*i+2]=mate[i];}
    for(int i=0;i<3*n;i++)Js[i]=1.0; // symmetric couplings for benchmark purposes
    for(int bi=0;bi<3;bi++){
      double beta=betas[bi];
      long steps = (long)(2e8/(n<100?100:n)); if(steps<2000000) steps=2000000; // keep each run ~0.1-1 s
      // dense naive
      for(int i=0;i<n;i++)sp[i]=(next()&1)?1:-1;
      long acc=0; double t0=now(); double sink=0;
      long stepsN = steps/ (n>=300? 4:1);
      for(long t=0;t<stepsN;t++){int i=next()%n; double f=0; const double*Ji=J+(long)i*n; for(int j=0;j<n;j++)f+=Ji[j]*sp[j];
        double dE=2*sp[i]*f; if(dE<=0||u01()<exp(-beta*dE)){sp[i]=-sp[i];acc++;}}
      double t1=now(); printf("%d,%.1f,dense_naive_O(n)_dE,%.2f,%.3f\n",n,beta,1e9*(t1-t0)/stepsN,(double)acc/stepsN);
      // dense with field cache
      for(int i=0;i<n;i++){double f=0;for(int j=0;j<n;j++)f+=J[i*n+j]*sp[j];h[i]=f;}
      acc=0; t0=now();
      for(long t=0;t<steps;t++){int i=next()%n; double dE=2*sp[i]*h[i];
        if(dE<=0||u01()<exp(-beta*dE)){sp[i]=-sp[i];acc++; double d=2*sp[i]; const double*Ji=J+(long)i*n; for(int j=0;j<n;j++)h[j]+=d*Ji[j];}}
      t1=now(); printf("%d,%.1f,dense_fieldcache,%.2f,%.3f\n",n,beta,1e9*(t1-t0)/steps,(double)acc/steps);
      // sparse 3-regular
      for(int i=0;i<n;i++)sp[i]=(next()&1)?1:-1;
      acc=0; t0=now(); long stepsS=steps*4;
      for(long t=0;t<stepsS;t++){int i=next()%n; double f=Js[3*i]*sp[nb[3*i]]+Js[3*i+1]*sp[nb[3*i+1]]+Js[3*i+2]*sp[nb[3*i+2]];
        double dE=2*sp[i]*f; if(dE<=0||u01()<exp(-beta*dE)){sp[i]=-sp[i];acc++;}}
      t1=now(); printf("%d,%.1f,sparse_3reg,%.2f,%.3f\n",n,beta,1e9*(t1-t0)/stepsS,(double)acc/stepsS);
      sink+=sp[0]; if(sink>1e300)printf("x");
    }
    free(J);free(sp);free(h);free(nb);free(Js);free(perm);free(mate);
  }
  return 0;
}
