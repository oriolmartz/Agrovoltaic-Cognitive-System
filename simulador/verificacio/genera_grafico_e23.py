"""Reprodueix la figura E23 a partir del CSV guardat, sense recalcular CLIPS.

Des de simulador/: python verificacio/genera_grafico_e23.py
Copia el PDF generat a figures/ del projecte d'Overleaf si es recompila.
"""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1]
data=root/'resultats/E23/E23_temps_tests.csv'
out=root/'resultats/E23/e23_temps.pdf'
rows=list(csv.DictReader(data.open(encoding='utf8',newline='')))
fig,ax=plt.subplots(figsize=(7.6,4.2))
for prefix,label in [('B_','B · Finestra'),('C_','C · Aleatori'),('D_','D · Antiguitat'),('E_','E · Activació episodi'),('F_','F · Activació grup'),('G_','G · Grup sense proteccions')]:
 pts=[(int(r['braç'].rsplit('_',1)[1]),float(r['ms_braç'])) for r in rows if r['braç'].startswith(prefix)]
 pts.sort()
 ax.plot([x for x,_ in pts],[y for _,y in pts],marker='o',linewidth=1.5,markersize=4,label=label)
a=round(float(rows[0]['ms_A']),1)
ax.axhline(a,linestyle='--',linewidth=1.4,color='black',alpha=.75,label=f'A · Sense oblit ({a:.1f} ms)')
ax.set_xticks([25,50,75],['25 %','50 %','75 %'])
ax.set_xlabel('Capacitat màxima respecte d’A')
ax.set_ylabel('Temps mitjà per cicle (ms)')
ax.set_title('E23 · Estratègies d’oblit (120 dies × 3 llavors)')
ax.grid(axis='y',alpha=.18)
ax.legend(ncol=2,fontsize=7.5,loc='upper left',frameon=False)
fig.tight_layout()
out.parent.mkdir(exist_ok=True,parents=True)
fig.savefig(out,metadata={'Title':'E23 temps per cicle','Subject':'Dades E23_temps_tests.csv del projecte'})
fig.savefig(out.with_suffix('.png'),dpi=155)
print('saved',out)
