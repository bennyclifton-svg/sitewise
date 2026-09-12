"""SiteWise colour specification: OKLCH masters, sRGB exports and contrast checks.

Oklab matrices: Bjorn Ottosson's public-domain reference implementation.
Contrast: WCAG relative luminance of final 8-bit sRGB equivalents, never OKLCH L.
No production frontend files are modified by this generator.
"""
import json
import math
from itertools import combinations
from pathlib import Path

OUT = Path(__file__).resolve().parent


def linear_rgb(l, c, h):
    a, b = c*math.cos(math.radians(h)), c*math.sin(math.radians(h))
    ll = (l + .3963377774*a + .2158037573*b)**3
    mm = (l - .1055613458*a - .0638541728*b)**3
    ss = (l - .0894841775*a - 1.2914855480*b)**3
    return (4.0767416621*ll-3.3077115913*mm+.2309699292*ss,
            -1.2684380046*ll+2.6097574011*mm-.3413193965*ss,
            -.0041960863*ll-.7034186147*mm+1.7076147010*ss)


def encode(v):
    return 12.92*v if v <= .0031308 else 1.055*v**(1/2.4)-.055


def decode(v):
    return v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4


def rgb_to_lab(rgb):
    r, g, b = rgb
    ll = (.4122214708*r+.5363325363*g+.0514459929*b)**(1/3)
    mm = (.2119034982*r+.6806995451*g+.1073969566*b)**(1/3)
    ss = (.0883024619*r+.2817188376*g+.6299787005*b)**(1/3)
    return (.2104542553*ll+.7936177850*mm-.0040720468*ss,
            1.9779984951*ll-2.4285922050*mm+.4505937099*ss,
            .0259040371*ll+.7827717662*mm-.8086757660*ss)


def colour(l, c, h):
    requested = c
    # Preserve lightness and hue; reduce chroma rather than clipping RGB channels.
    if not all(0 <= v <= 1 for v in linear_rgb(l, c, h)):
        low, high = 0, c
        for _ in range(36):
            mid = (low+high)/2
            if all(0 <= v <= 1 for v in linear_rgb(l, mid, h)):
                low = mid
            else:
                high = mid
        c = low*.999
    c = round(c, 6)
    values = linear_rgb(l, c, h)
    rgb = [round(255*encode(max(0, min(1, v)))) for v in values]
    return {'oklch': [l, c, h], 'hex': '#'+''.join(f'{v:02X}' for v in rgb),
            'css': f'oklch({l:.4f} {c:.6f} {h:g})',
            'requestedChroma': requested, 'gamutReduced': c < requested-1e-5}


P = {}
neutral_levels = [0, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
neutral_values = [(.992,.003,85),(.976,.006,85),(.948,.010,85),(.900,.014,85),
                  (.835,.017,80),(.730,.019,75),(.600,.020,70),(.470,.018,65),
                  (.405,.017,60),(.330,.016,58),(.267,.016,58),(.220,.012,58)]
for step, value in zip(neutral_levels, neutral_values):
    P[f'neutral-{step}'] = colour(*value)

# Achromatic dark surfaces keep Basalt's warmth out of large interface areas.
for step, lightness in [(950,.145),(900,.205),(800,.250),(700,.290),(600,.350),(500,.600),(400,.730)]:
    P[f'charcoal-{step}'] = colour(lightness, 0, 0)

steps = [50,100,200,300,400,500,600,700,800,900,950]
cyan_values = [(.974,.012,215),(.940,.027,215),(.886,.044,215),(.816,.064,215),
               (.744,.082,215),(.652,.097,214),(.553,.089,214),(.450,.073,213),
               (.360,.052,213),(.283,.032,213),(.225,.022,213)]
citron_values = [(.983,.014,109),(.965,.033,109),(.944,.059,109),(.920,.083,109),
                 (.883,.109,109),(.822,.125,109),(.710,.120,108),(.578,.103,108),
                 (.447,.075,107),(.328,.045,107),(.250,.025,107)]
for family, values in [('cyan',cyan_values),('citron',citron_values)]:
    for step, value in zip(steps, values):
        P[f'{family}-{step}'] = colour(*value)

semantic_colours = {
    'success': {'light':[(.968,.019,155),(.540,.085,155),(.420,.073,155),(.495,.095,155)],
                'dark':[(.295,.032,155),(.650,.094,155),(.835,.068,155),(.770,.100,155)]},
    'warning': {'light':[(.968,.030,78),(.550,.110,68),(.420,.083,60),(.510,.105,62)],
                'dark':[(.300,.032,65),(.705,.123,75),(.880,.080,80),(.805,.130,80)]},
    'error': {'light':[(.964,.019,25),(.550,.139,25),(.435,.122,25),(.510,.158,25)],
              'dark':[(.291,.034,25),(.680,.131,25),(.850,.054,25),(.775,.106,25)]},
}
for status, modes in semantic_colours.items():
    for mode, values in modes.items():
        for role, value in zip(['bg','border','text','icon'], values):
            P[f'{status}-{mode}-{role}'] = colour(*value)

light = {
    'canvas':'neutral-50','surface':'neutral-0','surface-elevated':'neutral-0','surface-inset':'neutral-100',
    'border-subtle':'neutral-100','border-default':'neutral-200','border-strong':'neutral-500','border-control':'neutral-500',
    'text-primary':'neutral-900','text-secondary':'neutral-700','text-tertiary':'neutral-600','text-inverse':'neutral-50',
    'action-primary':'citron-400','action-primary-hover':'citron-500','action-primary-pressed':'citron-600',
    'action-primary-text':'neutral-950','action-primary-border':'citron-800',
    'action-secondary':'neutral-900','action-secondary-hover':'neutral-800','action-secondary-pressed':'neutral-950',
    'action-secondary-text':'neutral-50','action-secondary-border':'neutral-900',
    'action-focus':'cyan-700','action-focus-gap':'neutral-0',
    'action-disabled-bg':'neutral-100','action-disabled-text':'neutral-600','action-disabled-border':'neutral-200',
    'link':'cyan-700','link-hover':'cyan-800','selection-bg':'cyan-100','selection-border':'cyan-600','selection-text':'cyan-800',
    'hover-bg':'neutral-50','pressed-bg':'neutral-100','input-bg':'neutral-0','input-text':'neutral-900','input-placeholder':'neutral-600',
    'info-bg':'cyan-50','info-border':'cyan-600','info-text':'cyan-800','info-icon':'cyan-700',
    'chart-surface':'neutral-0','chart-grid':'neutral-100','chart-label':'neutral-600','chart-separator':'neutral-0',
    'scene-ground':'cyan-300','scene-building':'neutral-50','scene-building-edge':'neutral-500',
    'scene-service-active':'cyan-700','scene-service-inactive':'neutral-400','scene-decision':'warning-light-icon',
    'map-line-decorative':'neutral-300','map-line-interactive':'cyan-700','map-lot-selected':'cyan-100',
}
dark = {
    'canvas':'charcoal-950','surface':'charcoal-900','surface-elevated':'charcoal-800','surface-inset':'charcoal-950',
    'border-subtle':'charcoal-700','border-default':'charcoal-600','border-strong':'charcoal-500','border-control':'charcoal-500',
    'text-primary':'neutral-100','text-secondary':'neutral-300','text-tertiary':'neutral-400','text-inverse':'neutral-950',
    'action-primary':'citron-500','action-primary-hover':'citron-400','action-primary-pressed':'citron-600',
    'action-primary-text':'neutral-950','action-primary-border':'citron-500',
    'action-secondary':'neutral-100','action-secondary-hover':'neutral-50','action-secondary-pressed':'neutral-200',
    'action-secondary-text':'neutral-950','action-secondary-border':'neutral-100',
    'action-focus':'cyan-300','action-focus-gap':'charcoal-900',
    'action-disabled-bg':'charcoal-800','action-disabled-text':'neutral-400','action-disabled-border':'charcoal-600',
    'link':'cyan-300','link-hover':'cyan-200','selection-bg':'cyan-900','selection-border':'cyan-500','selection-text':'cyan-200',
    'hover-bg':'charcoal-800','pressed-bg':'charcoal-700','input-bg':'charcoal-950','input-text':'neutral-100','input-placeholder':'neutral-400',
    'info-bg':'cyan-900','info-border':'cyan-500','info-text':'cyan-200','info-icon':'cyan-300',
    'chart-surface':'charcoal-900','chart-grid':'charcoal-700','chart-label':'neutral-400','chart-separator':'charcoal-900',
    'scene-ground':'cyan-900','scene-building':'neutral-100','scene-building-edge':'neutral-400',
    'scene-service-active':'cyan-700','scene-service-inactive':'neutral-400','scene-decision':'warning-light-icon',
    'map-line-decorative':'charcoal-600','map-line-interactive':'cyan-300','map-lot-selected':'cyan-900',
}
for mode, theme in [('light',light),('dark',dark)]:
    for status in semantic_colours:
        for role in ['bg','border','text','icon']:
            theme[f'{status}-{role}'] = f'{status}-{mode}-{role}'
    for role in ['bg','border','text','icon']:
        theme[f'danger-{role}'] = theme[f'error-{role}']

series = [
    ('Petrol',(.650,.094600,215),(.910,.062050,215),'circle','none'),
    ('Ochre',(.515,.108536,75),(.740,.122100,75),'square','8 3'),
    ('Denim',(.380,.125009,255),(.685,.107000,255),'triangle','2 3'),
    ('Terracotta',(.375,.131418,35),(.580,.125400,35),'diamond','10 3 2 3'),
    ('Evergreen',(.570,.072250,155),(.800,.082450,155),'plus','5 3'),
    ('Mulberry',(.350,.086700,335),(.590,.072250,335),'cross','12 4'),
    ('Olive',(.655,.106700,110),(.910,.103400,110),'triangle-down','2 2 8 2'),
    ('Graphite',(.455,.016000,70),(.690,.017000,70),'hexagon','12 3 3 3'),
]
for index, (name, lc, dc, shape, dash) in enumerate(series, 1):
    for mode, value, theme in [('light',lc,light),('dark',dc,dark)]:
        key = f'data-{mode}-{index}'
        P[key] = colour(*value)
        theme[f'data-{index}'] = key

THEMES = {'light':light, 'dark':dark}
BRAND = {'primary':'neutral-900','support':'cyan-300','functional-support':'cyan-700',
         'accent':'citron-400','atmosphere':'neutral-50'}


def rgb_hex(value):
    return [int(value[i:i+2],16)/255 for i in (1,3,5)]


def luminance(value):
    return sum(w*decode(v) for w,v in zip((.2126,.7152,.0722),rgb_hex(value)))


def contrast(a, b):
    lo, hi = sorted([luminance(a),luminance(b)])
    return (hi+.05)/(lo+.05)


checks = []
def check(mode, fg, bg, minimum, purpose, exception=False):
    theme = THEMES[mode]
    foreground, background = P[theme[fg]]['hex'], P[theme[bg]]['hex']
    ratio = contrast(foreground, background)
    actual = [sum(w*v for w,v in zip((.2126,.7152,.0722),linear_rgb(*P[theme[token]]['oklch']))) for token in (fg,bg)]
    ratio_oklch = (max(actual)+.05)/(min(actual)+.05)
    checks.append({'mode':mode,'foregroundToken':fg,'backgroundToken':bg,
                   'foreground':foreground,'background':background,'ratio':ratio,
                   'ratioOKLCH':ratio_oklch,'required':minimum,'pass':min(ratio,ratio_oklch)>=minimum,'purpose':purpose,'exception':exception})

for mode in THEMES:
    for text in ['text-primary','text-secondary','text-tertiary']:
        for bg in ['canvas','surface','surface-elevated','surface-inset']:
            check(mode,text,bg,4.5,'Normal text')
    for family in ['primary','secondary']:
        for state in ['', '-hover','-pressed']:
            check(mode,f'action-{family}-text',f'action-{family}{state}',4.5,'Enabled button label')
    for bg in ['canvas','surface','surface-elevated','surface-inset']:
        for fg in ['action-primary-border','border-control','action-focus']:
            check(mode,fg,bg,3,'Control boundary / offset focus ring')
        check(mode,'link',bg,4.5,'Underlined text link')
    for status in ['success','warning','error','info']:
        for fg, minimum in [('text',4.5),('icon',3),('border',3)]:
            check(mode,f'{status}-{fg}',f'{status}-bg',minimum,'Status '+fg)
    check(mode,'selection-text','selection-bg',4.5,'Selected item text')
    check(mode,'selection-border','selection-bg',3,'Selected item indicator')
    check(mode,'input-placeholder','input-bg',4.5,'Placeholder text')
    check(mode,'action-disabled-text','action-disabled-bg',4.5,'Inactive control; WCAG exempt',True)
    for i in range(1,9):
        check(mode,f'data-{i}','chart-surface',3,'Chart mark against chart surface')

CVD = {
    'protan':[[.152286,1.052583,-.204868],[.114503,.786281,.099216],[-.003882,-.048116,1.051998]],
    'deutan':[[.367322,.860646,-.227968],[.280085,.672501,.047413],[-.011820,.042940,.968881]],
    'tritan':[[1.255528,-.076749,-.178779],[-.078411,.930809,.147602],[.004733,.691367,.303900]],
}
cvd = {}
for mode, theme in THEMES.items():
    cvd[mode] = {}
    for kind, matrix in [('normal',None),*CVD.items()]:
        labs, simulated_hex = [], []
        for i in range(1,9):
            rgb = [decode(v) for v in rgb_hex(P[theme[f'data-{i}']]['hex'])]
            if matrix:
                rgb = [max(0,min(1,sum(a*b for a,b in zip(row,rgb)))) for row in matrix]
            labs.append(rgb_to_lab(rgb))
            simulated_hex.append('#'+''.join(f'{round(255*encode(v)):02X}' for v in rgb))
        distances = sorted([{'series':[a+1,b+1],'deltaEOK':math.dist(labs[a],labs[b])}
                            for a,b in combinations(range(8),2)],key=lambda item:item['deltaEOK'])
        cvd[mode][kind] = {'colours':simulated_hex,'closestPairs':distances[:3],
                           'interpretation':'Diagnostic only; labels, marker shapes and dashes remain required'}

tokens = {'name':'SiteWise — Chalk, Air & Citron','version':'1.1.0','status':'Approved production token specification; near-black dark surfaces',
          'colourSpace':'OKLCH D65; sRGB gamut, HEX fallback',
          'referenceSamples':{'method':'Median of broad hue/saturation bands; photographic reproduction, not original brand specifications',
                              'cyan':'#97CCDC','citron':'#DDDD87','charcoal':'#2A231D'},
          'brand':BRAND,'primitives':P,'themes':THEMES,
          'dataSeries':[{'index':i,'name':row[0],'marker':row[3],'dash':row[4]} for i,row in enumerate(series,1)],
          'gradient':{'angle':'118deg','space':'oklab','stops':[['neutral-50','0%'],['cyan-100','54%'],['cyan-300','100%']],
                      'use':'Marketing 3D/site field only; neutral copy panel, no gradient behind dense UI'},
          'contrast':checks,'colourVisionReview':cvd}
(OUT/'sitewise-colours.json').write_text(json.dumps(tokens,indent=2),encoding='utf-8')

css = ['/* SiteWise colour system 1.1.0 — generated from OKLCH masters. */',
       '/* Import deliberately; this file does not modify or alias the existing SPA theme. */', ':root {']
for key,value in P.items():
    css.append(f'  --sw-p-{key}: {value["hex"]};')
for key,value in BRAND.items():
    css.append(f'  --sw-brand-{key}: var(--sw-p-{value});')
css += ['}', '', '@supports (color: oklch(0.5 0.05 100)) {','  :root {']
for key,value in P.items():
    css.append(f'    --sw-p-{key}: {value["css"]};')
css += ['  }','}', '']
for mode,theme in THEMES.items():
    css.append((':root, [data-theme="light"]' if mode=='light' else '[data-theme="dark"]')+' {')
    css.append(f'  color-scheme: {mode};')
    for key,value in theme.items():
        css.append(f'  --sw-{key}: var(--sw-p-{value});')
    css.append('}')
css += ['', '/* House focus policy: use a gap matching the actual adjacent surface. */',
        '.sw-colour-scope :focus-visible {',
        '  outline: 2px solid var(--sw-action-focus);',
        '  outline-offset: 3px;',
        '  box-shadow: 0 0 0 3px var(--sw-action-focus-gap);',
        '}',
        '/* Token-only export. Status still requires a label/icon; charts require shapes/dashes. */']
(OUT/'sitewise-colours.css').write_text('\n'.join(css)+'\n',encoding='utf-8')

rows = ['# Measured contrast pairs','',
        'The table displays contrast calculated from the final 8-bit sRGB HEX values. Pass/fail checks both those values and the actual OKLCH masters, using unrounded ratios; JSON records both measurements. Displayed ratios are rounded to two decimals. Disabled controls are exempt, but their text is still tested as a house policy.',
        '', '| Mode | Foreground / background | HEX pair | Ratio | Minimum | Result |',
        '|---|---|---|---:|---:|---|']
for item in checks:
    rows.append(f'| {item["mode"]} | {item["foregroundToken"]} / {item["backgroundToken"]} | {item["foreground"]} / {item["background"]} | {item["ratio"]:.2f}:1 | {item["required"]}:1 | {"Pass" if item["pass"] else "Fail"}{" · exempt" if item["exception"] else ""} |')
(OUT/'CONTRAST.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
failures = [item for item in checks if not item['pass'] and not item['exception']]
print(json.dumps({'brand':{k:P[v] for k,v in BRAND.items()},'checks':len(checks),
                  'failures':failures,'gamutReduced':[k for k,v in P.items() if v['gamutReduced']],
                  'closestDataPairs':{m:{k:v['closestPairs'][0] for k,v in kinds.items()} for m,kinds in cvd.items()}},indent=2))
if failures:
    raise SystemExit('Adjust failed token pairs before release')
