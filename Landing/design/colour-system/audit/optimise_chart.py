"""Scratch candidate search; never edits canonical tokens."""
import ast
import json
import math
import random
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]
tree = ast.parse((BASE / 'build_colour_system.py').read_text())
keep = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))
        or isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('series', 'CVD') for t in node.targets)]
ns = {}
exec(compile(ast.Module(keep, type_ignores=[]), '<functions-only>', 'exec'), ns)
tokens = json.loads((BASE / 'sitewise-colours.json').read_text())


def variants(mode):
    output = []
    background = tokens['primitives'][tokens['themes'][mode]['chart-surface']]['hex']
    for row in ns['series']:
        old_l, old_c, hue = row[1 if mode == 'light' else 2]
        group = []
        for l in np.arange(.350 if mode == 'light' else .575, .671 if mode == 'light' else .911, .005):
            for factor in [.85, 1, 1.10]:
                colour = ns['colour'](round(float(l), 3), round(old_c * factor, 5), hue)
                ratio = ns['contrast'](colour['hex'], background)
                if ratio < 3.03:
                    continue
                rgb = [ns['decode'](v) for v in ns['rgb_hex'](colour['hex'])]
                labs = [ns['rgb_to_lab'](rgb)]
                for matrix in ns['CVD'].values():
                    sim = [max(0, min(1, sum(a*b for a,b in zip(line,rgb)))) for line in matrix]
                    labs.append(ns['rgb_to_lab'](sim))
                group.append({'colour':colour,'contrast':ratio,'labs':labs})
        output.append(group)
    return output


def search(mode):
    groups = variants(mode)
    pair_dist = {}
    for a in range(8):
        for b in range(a+1,8):
            aa = np.array([x['labs'] for x in groups[a]])
            bb = np.array([x['labs'] for x in groups[b]])
            all_d = np.linalg.norm(aa[:,None,:,:]-bb[None,:,:,:],axis=3)
            pair_dist[a,b] = all_d.min(axis=2)
    pairs=list(pair_dist)
    def score(state):
        distances = sorted(pair_dist[a,b][state[a], state[b]] for a,b in pairs)
        # Maximise the bottleneck primarily; smaller bonus spreads other near pairs.
        return distances[0] + .025*sum(distances[1:5])
    best_s, best_v = None, -1
    random.seed(20260908 + (mode == 'dark'))
    for restart in range(18):
        state=[random.randrange(len(g)) for g in groups]
        value=score(state)
        for step in range(15000):
            index=random.randrange(8)
            proposed=state.copy()
            proposed[index]=random.randrange(len(groups[index]))
            candidate=score(proposed)
            t=.010*(1-step/15000)**3 + .00005
            if candidate>value or random.random()<math.exp(min(0,(candidate-value)/t)):
                state,value=proposed,candidate
                if value>best_v:
                    best_s,best_v=state.copy(),value
    chosen=[groups[i][choice] for i,choice in enumerate(best_s)]
    result={'mode':mode,'series':[{'name':ns['series'][i][0],**entry['colour'],'contrast':entry['contrast']} for i,entry in enumerate(chosen)],'reviews':{}}
    for k,kind in enumerate(['normal','protan','deutan','tritan']):
        distances=sorted([{'names':[ns['series'][a][0],ns['series'][b][0]],'deltaEOK':math.dist(chosen[a]['labs'][k],chosen[b]['labs'][k])} for a,b in pairs],key=lambda d:d['deltaEOK'])
        result['reviews'][kind]=distances[:3]
    print(json.dumps(result),flush=True)
    return result

if __name__=='__main__':
    results={mode:search(mode) for mode in ['light','dark']}
    (Path(__file__).parent/'chart-candidates.json').write_text(json.dumps(results,indent=2))
